# Feedback Mode 存储功能实现总结

## 问题背景

用户提出：retry 时如何指定 feedback 的评估模式（`--mode`）？

**核心困境**：
- `/generate` 无参数，retry 时无需额外配置
- `/feedback <task_id> --mode <mode>` 有参数，retry 时需要知道用哪个模式

## 解决方案

采用**简化方案**：
1. **存储评估模式**：`/feedback` 执行时保存到 `task.feedback_mode`
2. **智能默认**：retry 时优先使用存储的模式
3. **支持覆盖**：retry 时可通过 `--mode` 参数改变模式

## 实现细节

### 1. 数据模型扩展

```python
# src/workflow/task_manager.py

class GenerationTask:
    # 新增字段
    feedback_mode: Optional[str] = None  # "auto", "llm_judge", "human"
```

### 2. /feedback 命令存储模式

```python
# examples/workflow_cli.py (line 849-865)

# 确定实际使用的模式
if evaluation_mode is None:
    ace_config = get_ace_config()
    actual_mode = ace_config.training.feedback_source  # 从配置读取
else:
    actual_mode = evaluation_mode

# ✅ 存储到任务
task.feedback_mode = actual_mode
task_manager._save_task(task)
```

### 3. /retry 命令支持 --mode

```python
# examples/workflow_cli.py (line 737-747)

if "--mode" in cmd_parts:
    override_mode = cmd_parts[mode_idx + 1]
    if override_mode not in ["auto", "llm_judge", "human"]:
        print("不支持的评估模式")
        continue

retry_handler.handle(
    task_id=task_id,
    override_mode=override_mode  # ✅ 新增参数
)
```

### 4. RetryCommandHandler 使用模式

```python
# src/workflow/command_handler.py (line 485-512)

# 确定评估模式（三级优先级）
if override_mode:
    evaluation_mode = override_mode  # 1. CLI参数
    mode_source = "命令行参数"
elif task.feedback_mode:
    evaluation_mode = task.feedback_mode  # 2. 存储的配置
    mode_source = "之前存储的配置"
else:
    evaluation_mode = ace_config.training.feedback_source  # 3. 配置默认值
    mode_source = "配置文件默认值"

# 更新存储（如果使用override）
if override_mode and override_mode != task.feedback_mode:
    task.feedback_mode = override_mode
    task_manager._save_task(task)

# 启动 feedback_worker
print(f"   评估模式: {evaluation_mode} (来源: {mode_source})")
self.task_scheduler._start_process(
    target_func=run_feedback_workflow,
    args=(task_id, evaluation_mode)  # ✅ 传递模式
)
```

## 使用示例

### 场景1: 正常流程（自动存储和复用）

```bash
# Step 1: 执行 feedback
👤 你: /feedback a6ff5f06 --mode llm_judge

🚀 启动反馈训练流程（llm_judge模式）
# → task.feedback_mode = "llm_judge" (已存储)

# Step 2: 失败了
[evaluating阶段失败：datetime序列化错误]

# Step 3: 修复代码后 retry
👤 你: /retry a6ff5f06

🔄 准备重试任务 a6ff5f06
  失败阶段: evaluating

✅ 重试准备完成
🚀 正在启动Feedback工作进程...
   评估模式: llm_judge (来源: 之前存储的配置)  # ✅ 自动使用
```

### 场景2: Retry 时改变模式

```bash
# 之前用的 llm_judge，现在想改用 auto
👤 你: /retry a6ff5f06 --mode auto

🔄 准备重试任务 a6ff5f06
  失败阶段: evaluating

✅ 重试准备完成
🚀 正在启动Feedback工作进程...
   评估模式: auto (来源: 命令行参数)  # ✅ 使用新模式

# → task.feedback_mode = "auto" (已更新)
```

### 场景3: 旧任务（无存储模式）

```bash
# 重试旧任务
👤 你: /retry old_task_id

🔄 准备重试任务 old_task_id
  失败阶段: evaluating

✅ 重试准备完成
🚀 正在启动Feedback工作进程...
   评估模式: auto (来源: 配置文件默认值)  # ✅ 降级到默认值
```

## 优先级逻辑

```
┌─────────────────────────────────┐
│  /retry <task_id> --mode auto   │  ← 优先级 1（最高）
└─────────────┬───────────────────┘
              ↓
        override_mode
              ↓
┌─────────────────────────────────┐
│  task.feedback_mode (存储的)    │  ← 优先级 2
└─────────────┬───────────────────┘
              ↓ (如果为 None)
┌─────────────────────────────────┐
│  ace_config.training.           │  ← 优先级 3（最低）
│  feedback_source                │
└─────────────────────────────────┘
```

## 文件变更清单

```
✅ src/workflow/task_manager.py
   - 添加 feedback_mode 字段

✅ examples/workflow_cli.py
   - /feedback 命令：存储 mode
   - /retry 命令：解析 --mode 参数

✅ src/workflow/command_handler.py
   - RetryCommandHandler.handle()：添加 override_mode 参数
   - 实现三级优先级逻辑
   - 显示模式来源信息

✅ docs/FEEDBACK_MODE_STORAGE.md
   - 完整的使用文档

✅ docs/RETRY_WITH_MODE_SUMMARY.md
   - 实现总结（本文档）
```

## 关键设计决策

### 1. 为什么只有 feedback 需要存储参数？

**分析**：
- `/generate` 无参数 → retry 时直接重新执行
- `/feedback --mode <mode>` 有参数 → 需要知道用哪个

**结论**：只需为 feedback 设计存储机制

### 2. 为什么不用 --from-manual 方案？

**原始提议**：
- 深度较深的阶段自动重试
- 深度为0的阶段提示手动重新执行

**问题**：
- 过度设计（主任务没有参数，不需要这么复杂）
- 用户体验差（需要记住命令）

**最终方案**：
- 简单直接：存储+复用
- 灵活：支持覆盖

### 3. 为什么支持 --mode 覆盖？

**场景**：
- 之前用 `llm_judge`，发现太慢
- retry 时想改用 `auto`

**不支持覆盖**：
```bash
/retry abc123  # 仍然用 llm_judge
# 必须重新 /feedback abc123 --mode auto
```

**支持覆盖**：
```bash
/retry abc123 --mode auto  # 直接改用 auto
# 更方便！
```

## 边缘情况处理

| 情况 | 处理 |
|------|------|
| `/feedback` 不指定 `--mode` | 使用配置默认值并存储 |
| 旧任务无 `feedback_mode` 字段 | 降级到配置默认值 |
| retry 时覆盖 mode | 更新存储到 task.json |
| 主任务阶段 retry | 不涉及 mode，忽略 `--mode` 参数 |

## 测试建议

### 测试1: 存储和复用

```bash
# 1. 执行 feedback
/feedback test123 --mode llm_judge

# 2. 验证存储
cat logs/generation_tasks/test123/task.json | grep feedback_mode
# 预期: "feedback_mode": "llm_judge"

# 3. Retry（不带 --mode）
/retry test123

# 4. 验证使用了存储的模式
/logs test123 --tail 10
# 预期输出: "评估模式: llm_judge (来源: 之前存储的配置)"
```

### 测试2: 覆盖模式

```bash
# 1. Retry 并覆盖
/retry test123 --mode auto

# 2. 验证更新
cat logs/generation_tasks/test123/task.json | grep feedback_mode
# 预期: "feedback_mode": "auto"
```

### 测试3: 旧任务兼容性

```bash
# 1. 手动删除 feedback_mode 字段模拟旧任务
jq 'del(.feedback_mode)' logs/generation_tasks/test123/task.json > temp.json
mv temp.json logs/generation_tasks/test123/task.json

# 2. Retry
/retry test123

# 3. 验证使用配置默认值
/logs test123 --tail 10
# 预期输出: "评估模式: auto (来源: 配置文件默认值)"
```

## 总结

**实现成果**：
- ✅ 智能存储评估模式
- ✅ 三级优先级逻辑
- ✅ 支持运行时覆盖
- ✅ 向后兼容旧任务
- ✅ 清晰的用户反馈

**用户体验**：
- 📍 简化操作：retry 无需重复指定参数
- 📍 灵活调整：随时可改变评估策略
- 📍 透明可控：明确显示模式来源

**代码质量**：
- 📍 职责清晰：存储、读取、覆盖分离
- 📍 易于扩展：未来可添加更多评估模式
- 📍 健壮性强：多层降级机制

现在你可以放心地使用 `/retry a6ff5f06` 来重试你的失败任务了！🎉
