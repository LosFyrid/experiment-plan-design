# Task Retry Mechanism Design

## 问题背景

当任务失败（FAILED状态）后，用户无法重新执行，需要一个完善的重试机制。

## 设计目标

1. **支持智能重试**：根据失败阶段选择重试策略
2. **防止无限重试**：限制重试次数
3. **数据一致性**：处理部分生成的文件
4. **边缘情况**：处理子进程、文件损坏、不可重试错误等

---

## 核心设计

### 1. 任务状态扩展

在 `GenerationTask` 中添加重试相关字段：

```python
class GenerationTask:
    # 现有字段
    task_id: str
    status: TaskStatus
    error: Optional[str]

    # 新增字段
    retry_count: int = 0              # 当前重试次数
    max_retries: int = 3              # 最大重试次数（可配置）
    failed_stage: Optional[str] = None  # 失败阶段标识
    retry_history: List[Dict] = []    # 重试历史记录
```

### 2. 失败阶段标识

**主任务阶段（task_worker.py）：**
- `extracting` - 需求提取失败
- `retrieving` - RAG检索失败
- `generating` - 方案生成失败

**反馈流程阶段（feedback_worker.py）：**
- `evaluating` - 评估失败
- `reflecting` - 反思失败
- `curating` - 策展失败

### 3. 重试策略

#### 策略A: 部分重试（默认）
- **原则**：保留成功步骤的结果，从失败点继续
- **适用**：网络波动、API限流等暂时性错误
- **实现**：根据 `failed_stage` 恢复到对应状态

| failed_stage | 恢复到的状态 | 保留的文件 |
|--------------|--------------|------------|
| `extracting` | PENDING | 无 |
| `retrieving` | AWAITING_CONFIRM | requirements.json |
| `generating` | RETRIEVING | requirements.json, templates.json |
| `evaluating` | COMPLETED | plan.json, generation_result.json |
| `reflecting` | COMPLETED | 所有生成文件 + feedback.json |
| `curating` | COMPLETED | 所有生成文件 + reflection.json |

#### 策略B: 完全重试
- **原则**：清理所有中间文件，从头开始
- **适用**：数据损坏、逻辑错误
- **触发**：`/retry <task_id> --clean`

### 4. 边缘情况处理

#### 4.1 子进程仍在运行

```python
if task.status == TaskStatus.FAILED:
    # 检查并终止残留子进程
    if task_id in scheduler.processes:
        print("⚠️  检测到残留子进程，正在终止...")
        scheduler.terminate_task(task_id)
        time.sleep(1)  # 等待进程完全退出
```

#### 4.2 文件完整性验证

```python
def validate_and_clean_files(task: GenerationTask, stage: str):
    """验证文件完整性，损坏则删除"""

    if stage in ["retrieving", "generating", "evaluating"]:
        # 检查 requirements.json
        if task.requirements_file.exists():
            try:
                req = task.load_requirements()
                if not req or not req.get("objective"):
                    raise ValueError("Requirements incomplete")
            except:
                print("⚠️  requirements.json 已损坏，将重新提取")
                task.requirements_file.unlink()
                return "extracting"  # 回退到更早阶段

    # 类似检查其他文件...
    return stage
```

#### 4.3 重试次数限制

```python
if task.retry_count >= task.max_retries:
    print(f"❌ 任务已达到最大重试次数 ({task.max_retries})")
    print(f"   - 使用 '/retry {task_id} --clean' 完全重新开始")
    print(f"   - 使用 '/retry {task_id} --force' 强制重试（忽略次数限制）")
    return False
```

#### 4.4 不可重试的错误

```python
NON_RETRYABLE_ERRORS = [
    "配置文件不存在",
    "Playbook不存在",
    "API密钥无效",
    "模型不存在",
    "权限不足"
]

def is_retryable(error_msg: str) -> bool:
    """判断错误是否可重试"""
    for pattern in NON_RETRYABLE_ERRORS:
        if pattern in error_msg:
            return False
    return True

if not is_retryable(task.error):
    print(f"❌ 此错误不可重试: {task.error}")
    print("   请先修复配置问题")
    return False
```

#### 4.5 并发重试保护

```python
# 检查是否有其他进程正在重试同一任务
RETRY_LOCK_FILE = task.task_dir / ".retry_lock"

if RETRY_LOCK_FILE.exists():
    print("⚠️  任务正在被另一个进程重试")
    return False

# 创建锁文件
RETRY_LOCK_FILE.touch()
try:
    # 执行重试
    ...
finally:
    RETRY_LOCK_FILE.unlink(missing_ok=True)
```

#### 4.6 feedback流程特殊处理

```python
# feedback流程失败后，不影响主任务状态
# 主任务保持 COMPLETED，仅标记 feedback 失败

class GenerationTask:
    feedback_status: Optional[str] = None  # "pending", "running", "completed", "failed"
    feedback_error: Optional[str] = None
    feedback_retry_count: int = 0
```

---

## CLI命令设计

### `/retry <task_id> [options]`

**选项：**
- 无选项：部分重试（默认）
- `--clean`：完全重试，清理所有文件
- `--force`：忽略重试次数限制
- `--stage <stage>`：手动指定从哪个阶段重试

**示例：**
```bash
# 部分重试（从失败点继续）
/retry a6ff5f06

# 完全重试（从头开始）
/retry a6ff5f06 --clean

# 强制重试（即使超过次数限制）
/retry a6ff5f06 --force

# 手动指定从生成阶段重试
/retry a6ff5f06 --stage generating
```

**输出示例：**
```
🔄 准备重试任务 a6ff5f06
  ✅ 任务状态: FAILED
  ✅ 失败阶段: evaluating
  ✅ 重试次数: 1/3
  ✅ 错误可重试

📋 重试策略: 部分重试
  - 保留文件: plan.json, generation_result.json
  - 从评估阶段重新开始

🚀 正在启动重试进程...
  进程ID: 12345

💡 查看实时日志: /logs a6ff5f06 --tail 50
```

---

## 实现计划

### Phase 1: 数据模型扩展
- [ ] 扩展 `GenerationTask` 类
- [ ] 添加 `retry_history` 序列化逻辑
- [ ] 修改 `task.json` 结构

### Phase 2: 失败追踪
- [ ] 修改 `task_worker.py` 异常处理
- [ ] 修改 `feedback_worker.py` 异常处理
- [ ] 统一异常捕获和记录

### Phase 3: 重试逻辑
- [ ] 实现 `RetryHandler` 类
- [ ] 文件验证和清理逻辑
- [ ] 状态恢复逻辑

### Phase 4: CLI集成
- [ ] 添加 `/retry` 命令
- [ ] 实现命令行参数解析
- [ ] 添加交互式确认

### Phase 5: 测试
- [ ] 单元测试（各个阶段失败）
- [ ] 集成测试（重试流程）
- [ ] 边缘情况测试

---

## 安全考虑

1. **防止数据丢失**：清理文件前创建备份
2. **日志保留**：重试时不覆盖原日志，使用追加模式
3. **原子操作**：状态更新使用文件锁
4. **用户确认**：`--clean` 模式需要二次确认

---

## 未来扩展

1. **智能重试间隔**：指数退避策略
2. **错误分类**：自动识别错误类型并推荐重试策略
3. **批量重试**：`/retry --all-failed` 重试所有失败任务
4. **重试通知**：重试完成后通知用户
