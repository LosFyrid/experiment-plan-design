# Task Retry Mechanism - 用户指南

## 概述

当任务失败时（FAILED状态），你可以使用 `/retry` 命令智能地重试任务，而不需要从头开始。

## 快速开始

### 基础用法

```bash
# 查看失败任务的状态
/status

# 部分重试（默认）- 从失败点继续
/retry a6ff5f06

# 完全重试 - 清理所有文件，从头开始
/retry a6ff5f06 --clean

# 强制重试 - 忽略重试次数限制
/retry a6ff5f06 --force

# 手动指定重试阶段
/retry a6ff5f06 --stage generating
```

## 重试策略

### 1. 部分重试（推荐，默认行为）

**适用场景**：
- 网络波动导致的临时错误
- API限流
- 临时性系统资源不足

**工作原理**：
- 保留已成功步骤的结果文件
- 从失败阶段重新开始执行
- 节省时间和API调用次数

**示例**：
```bash
# 任务在"生成方案"阶段失败
# 将保留 requirements.json 和 templates.json
# 仅重新执行生成步骤
/retry abc123
```

**各阶段重试行为**：

| 失败阶段 | 保留文件 | 删除文件 | 从何处恢复 |
|---------|---------|---------|-----------|
| extracting | 无 | requirements.json | PENDING（重新提取） |
| retrieving | requirements.json | templates.json | AWAITING_CONFIRM |
| generating | requirements.json, templates.json | plan.json, generation_result.json | RETRIEVING（重新生成） |
| evaluating | 生成文件 | feedback.json | COMPLETED（重新评估） |
| reflecting | 生成+反馈文件 | reflection.json | COMPLETED（重新反思） |
| curating | 生成+反馈+反思 | curation.json | COMPLETED（重新策展） |

### 2. 完全重试（清理模式）

**适用场景**：
- 数据文件损坏
- 需求发生重大变化
- 部分重试多次失败

**工作原理**：
- 删除所有中间文件（仅保留 config.json 和 task.json）
- 从PENDING状态重新开始
- 确保干净的执行环境

**示例**：
```bash
# 清理所有文件，从头开始
/retry abc123 --clean
```

## 安全机制

### 1. 重试次数限制

默认最多重试3次，防止无限循环：

```bash
# 已重试3次后
/retry abc123
# ❌ 无法重试: 已达到最大重试次数 (3/3)

# 使用 --force 忽略限制
/retry abc123 --force
# ✅ 强制重试
```

### 2. 不可重试错误检测

某些错误不应重试（需要人工修复）：

**不可重试的错误**：
- `配置文件不存在`
- `Playbook不存在`
- `API密钥无效`
- `模型不存在`
- `权限不足`

**示例**：
```bash
# 配置错误
/retry abc123
# ❌ 无法重试: 此错误不可重试: 配置文件不存在

# 修复配置后，使用 --force 重试
vim configs/ace_config.yaml
/retry abc123 --force
```

### 3. 文件完整性验证

重试前自动验证保留文件的完整性：

- 检查文件是否存在
- 验证JSON格式是否有效
- 验证必需字段是否存在

**损坏文件处理**：
```
🔍 验证文件完整性...
  ⚠️  发现损坏文件: requirements.json
  ⚠️  建议使用 --clean 模式完全重试

🗑️  清理文件...
  🗑️  已删除: requirements.json
```

### 4. 子进程残留处理

重试前自动清理残留的子进程：

```
⚠️  检测到残留子进程，正在终止...
✅ 子进程已终止
```

## 实际使用示例

### 场景1: 生成阶段失败（网络问题）

```bash
# Step 1: 查看失败任务
👤 你: /status

======================================================================
任务状态: ❌ FAILED
======================================================================
  任务ID: a6ff5f06
  失败阶段: generating
  重试次数: 0/3

❌ 失败原因: 生成失败: Request timeout

💡 重试选项:
  /retry a6ff5f06              # 部分重试（从失败点继续）
  /retry a6ff5f06 --clean      # 完全重试（从头开始）
  /retry a6ff5f06 --force      # 强制重试（忽略次数限制）

# Step 2: 部分重试（推荐）
👤 你: /retry a6ff5f06

🔄 准备重试任务 a6ff5f06
  ✅ 任务状态: failed
  ✅ 失败阶段: generating
  ✅ 重试次数: 0/3

📋 重试策略: 部分重试
  - 从阶段开始: generating
  - 恢复到状态: retrieving
  - 保留文件: requirements.json, templates.json

🔍 验证文件完整性...
  ✅ 所有文件完整

✅ 重试准备完成
  - 任务状态已更新: retrieving
  - 重试次数: 1/3

🚀 正在启动任务工作进程...

💡 查看实时日志: /logs a6ff5f06 --tail 50

# Step 3: 查看日志
👤 你: /logs a6ff5f06 --tail 20
```

### 场景2: 评估失败（JSON序列化错误）

**修复前的失败**：
```bash
👤 你: /status

任务状态: ❌ FAILED
  失败阶段: evaluating
  失败原因: 评估失败: Object of type datetime is not JSON serializable

# 查看代码，发现是datetime序列化问题
# 修复代码后重试

👤 你: /retry abc123

✅ 重试准备完成
🚀 正在启动Feedback工作进程...
```

### 场景3: 多次失败后完全重试

```bash
# 第1次重试失败
👤 你: /retry abc123
# ... 仍然失败

# 第2次重试失败
👤 你: /retry abc123
# ... 仍然失败

# 第3次重试失败
👤 你: /retry abc123
# ... 仍然失败

# 已达到重试次数限制
👤 你: /retry abc123
❌ 无法重试: 已达到最大重试次数 (3/3)

# 决定完全重试
👤 你: /retry abc123 --clean --force

📋 重试策略: 完全重试
  - 从阶段开始: extracting
  - 恢复到状态: pending

🗑️  清理文件...
  🗑️  已删除: requirements.json
  🗑️  已删除: templates.json
  🗑️  已删除: plan.json
  🗑️  已删除: generation_result.json

✅ 重试准备完成
```

## 最佳实践

### 1. 优先使用部分重试

- 速度更快
- 成本更低（节省API调用）
- 保留有效数据

### 2. 何时使用完全重试

- 部分重试多次失败
- 怀疑中间文件损坏
- 需求发生重大变化

### 3. 查看日志排查问题

```bash
# 失败后先查看日志
cat logs/generation_tasks/abc123/task.log

# 或使用CLI命令
/logs abc123 --tail 100

# 定位错误原因后再决定重试策略
```

### 4. 合理使用 --force

- 仅在确认问题已修复后使用
- 避免对配置错误使用 --force
- 优先修复根本原因

## 重试历史追踪

每次重试都会记录在 `retry_history` 中：

```json
{
  "retry_history": [
    {
      "timestamp": "2025-10-27T13:00:00",
      "retry_count": 1,
      "previous_error": "生成失败: Request timeout",
      "previous_stage": "generating",
      "strategy": "partial"
    },
    {
      "timestamp": "2025-10-27T13:05:00",
      "retry_count": 2,
      "previous_error": "生成失败: Rate limit exceeded",
      "previous_stage": "generating",
      "strategy": "partial"
    }
  ]
}
```

可以通过日志分析重试模式，优化系统稳定性。

## 故障排除

### 问题1: 重试后仍然失败

**解决方案**：
1. 查看详细日志定位根本原因
2. 检查是否为系统性问题（API密钥、配置等）
3. 尝试 `--clean` 模式
4. 如果是代码bug，修复后再重试

### 问题2: 重试次数限制

**解决方案**：
```bash
# 检查是否真的需要重试
# 如果确认问题已修复，使用 --force
/retry abc123 --force

# 如果想完全重新开始，使用 --clean + --force
/retry abc123 --clean --force
```

### 问题3: 文件损坏

**解决方案**：
```bash
# 系统会自动检测并删除损坏文件
# 或手动使用 --clean 清理所有文件
/retry abc123 --clean
```

## 技术细节

### 状态转换图

```
FAILED (failed_stage=generating)
  │
  ├─ 部分重试 → RETRIEVING → 继续执行
  │
  └─ 完全重试 → PENDING → 从头开始

FAILED (failed_stage=evaluating)
  │
  └─ 重试 → COMPLETED → 重新运行feedback_worker
```

### 文件清理规则

重试时自动清理的文件：
- 部分重试：仅清理失败阶段及之后的文件
- 完全重试：清理除 config.json 和 task.json 外的所有文件

### 子进程管理

- 重试前自动终止残留子进程
- 等待1秒确保进程完全退出
- 根据恢复状态选择启动 task_worker 或 feedback_worker

## 总结

重试机制提供了智能、安全、高效的任务恢复能力：

✅ **智能** - 根据失败阶段自动选择最优策略
✅ **安全** - 防止无限重试和数据损坏
✅ **高效** - 保留有效数据，节省时间和成本
✅ **灵活** - 支持多种模式和选项

使用重试机制可以显著提高系统的容错能力和用户体验！
