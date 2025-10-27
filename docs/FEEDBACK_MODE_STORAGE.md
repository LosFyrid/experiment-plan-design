# Feedback Mode 存储与重试机制

## 概述

为了简化重试流程，系统会自动存储 feedback 的评估模式（`--mode` 参数），在重试时复用之前的配置。

## 工作流程

### 1. 首次执行 /feedback

```bash
# 执行 feedback 并指定模式
👤 你: /feedback abc123 --mode llm_judge

# 系统行为：
# 1. 确定评估模式：llm_judge（用户指定）
# 2. 存储到任务：task.feedback_mode = "llm_judge"
# 3. 启动 feedback_worker (mode=llm_judge)
```

**无参数情况**：
```bash
# 不指定 --mode，使用配置默认值
👤 你: /feedback abc123

# 系统行为：
# 1. 从配置读取：ace_config.training.feedback_source（例如 "auto"）
# 2. 存储到任务：task.feedback_mode = "auto"
# 3. 启动 feedback_worker (mode=auto)
```

### 2. Feedback 失败后重试

```bash
# 场景：evaluating 阶段失败（datetime 序列化错误）
👤 你: /retry abc123

# 系统行为：
# 1. 读取存储的模式：task.feedback_mode = "llm_judge"
# 2. 清理损坏文件：feedback.json
# 3. 启动 feedback_worker (mode=llm_judge)
# 4. 输出：
🔄 准备重试任务 abc123
  失败阶段: evaluating
  评估模式: llm_judge (来源: 之前存储的配置)

✅ 重试准备完成
🚀 正在启动Feedback工作进程...
   评估模式: llm_judge (来源: 之前存储的配置)
```

### 3. 重试时覆盖模式

```bash
# 想改用其他评估模式
👤 你: /retry abc123 --mode auto

# 系统行为：
# 1. 使用新模式：auto（命令行参数优先）
# 2. 更新存储：task.feedback_mode = "auto"
# 3. 启动 feedback_worker (mode=auto)
# 4. 输出：
🚀 正在启动Feedback工作进程...
   评估模式: auto (来源: 命令行参数)
```

## 模式优先级

```
override_mode (--mode 参数)
    ↓
task.feedback_mode (存储的模式)
    ↓
config.default_mode (配置文件默认值)
```

**代码逻辑**：
```python
if override_mode:
    evaluation_mode = override_mode  # 优先级1: CLI参数
elif task.feedback_mode:
    evaluation_mode = task.feedback_mode  # 优先级2: 存储的模式
else:
    evaluation_mode = ace_config.training.feedback_source  # 优先级3: 配置默认值
```

## 使用场景

### 场景1: 正常重试（使用之前的模式）

```bash
# 首次执行
/feedback abc123 --mode llm_judge
# → 失败 (datetime 序列化错误)

# 修复代码后重试
/retry abc123
# → 自动使用 llm_judge 模式
```

**优点**：
- ✅ 无需记住之前用的什么模式
- ✅ 行为一致性

### 场景2: 改变评估策略

```bash
# 首次使用 LLM 评估
/feedback abc123 --mode llm_judge
# → 发现太慢或太贵

# 改用规则评估重试
/retry abc123 --mode auto
# → 使用 auto 模式，并更新存储
```

**优点**：
- ✅ 灵活调整评估策略
- ✅ 更新后的模式会被保存（下次retry时继续使用）

### 场景3: 旧任务没有存储模式

```bash
# 重试旧任务（没有 feedback_mode 字段）
/retry old_task

# 系统行为：
# 1. 检测到 task.feedback_mode = None
# 2. 使用配置默认值：ace_config.training.feedback_source
# 3. 警告：⚠️ 未找到之前的评估模式，使用配置默认值
```

## 数据存储

### GenerationTask 字段

```python
class GenerationTask:
    feedback_mode: Optional[str] = None  # "auto", "llm_judge", "human"
```

### task.json 示例

```json
{
  "task_id": "abc123",
  "status": "completed",
  "feedback_status": "failed",
  "feedback_mode": "llm_judge",  // ✅ 存储的评估模式
  "failed_stage": "evaluating",
  "retry_count": 1,
  ...
}
```

## 命令参考

### /feedback 命令

```bash
# 使用配置默认模式
/feedback <task_id>

# 指定评估模式
/feedback <task_id> --mode auto
/feedback <task_id> --mode llm_judge
/feedback <task_id> --mode human
```

**效果**：
- 存储指定的（或默认的）模式到 `task.feedback_mode`
- 启动 feedback_worker

### /retry 命令

```bash
# 使用存储的模式
/retry <task_id>

# 覆盖评估模式
/retry <task_id> --mode auto
/retry <task_id> --mode llm_judge

# 组合使用
/retry <task_id> --clean --mode auto  # 完全重试 + 改用auto模式
```

**效果**：
- 如果指定 `--mode`，使用新模式并更新存储
- 如果未指定，使用存储的模式（或配置默认值）

## 配置文件

### configs/ace_config.yaml

```yaml
training:
  feedback_source: "auto"  # 默认评估模式

  # 可选值：
  # - auto: 基于规则的自动评估（快速，免费）
  # - llm_judge: LLM评估（准确，消耗tokens）
  # - human: 人工评分（待实现）
```

**作用**：
- 当 `/feedback` 不指定 `--mode` 时，使用此默认值
- 当 `/retry` 没有存储模式时，使用此默认值

## 常见问题

### Q1: 为什么主任务（/generate）不需要存储参数？

**A**: `/generate` 命令没有参数，retry 时直接重新执行即可，无需存储配置。

### Q2: 如果我想永久改变默认模式怎么办？

**A**: 修改配置文件：
```bash
vim configs/ace_config.yaml
# 修改 training.feedback_source
```

### Q3: 存储的 mode 会影响其他任务吗？

**A**: 不会。每个任务独立存储自己的 `feedback_mode`。

### Q4: 如果 feedback_worker 内部再次失败，mode 会丢失吗？

**A**: 不会。mode 存储在 `task.json`，持久化到磁盘。即使进程崩溃，下次 retry 仍然可以读取。

## 实现细节

### 存储时机

1. **/feedback 命令执行时**
   ```python
   # examples/workflow_cli.py
   task.feedback_mode = actual_mode
   task_manager._save_task(task)
   ```

2. **retry 覆盖时**
   ```python
   # src/workflow/command_handler.py
   if override_mode and override_mode != task.feedback_mode:
       task.feedback_mode = override_mode
       task_manager._save_task(task)
   ```

### 读取逻辑

```python
# src/workflow/command_handler.py: RetryCommandHandler.handle()

# 确定评估模式
if override_mode:
    evaluation_mode = override_mode  # 命令行参数
elif task.feedback_mode:
    evaluation_mode = task.feedback_mode  # 存储的配置
else:
    evaluation_mode = ace_config.training.feedback_source  # 配置默认值
```

## 总结

**设计理念**：
- ✅ **智能默认**：自动记住之前的选择
- ✅ **灵活覆盖**：支持临时改变策略
- ✅ **向后兼容**：旧任务自动使用配置默认值
- ✅ **简化操作**：用户无需重复输入参数

通过存储评估模式，retry 操作变得更加智能和便捷！
