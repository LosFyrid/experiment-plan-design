# 工作流系统使用指南

本文档介绍如何使用完整的实验方案设计工作流系统。

## 系统架构

```
用户 ←→ Chatbot (MOSES)
         ↓
      /generate 命令触发
         ↓
    后台任务系统
         ↓
    1. 提取需求 (LLM)
    2. 等待用户确认 ⏸️
    3. RAG检索模板
    4. Generator生成方案
         ↓
    持久化到文件
```

## 核心特性

- ✅ **后台任务执行**：CLI退出后任务继续运行
- ✅ **持久化存储**：所有中间数据保存到文件
- ✅ **主动提醒**：需要用户确认时自动提醒
- ✅ **文件锁机制**：防止多实例冲突
- ✅ **优雅关闭**：工作线程安全销毁
- ✅ **空闲超时**：5分钟无活动自动退出

## 快速开始

### 1. 启动主CLI

```bash
python examples/workflow_cli.py
```

### 2. 与Chatbot对话

```
👤 你: 我想合成阿司匹林

🤖 助手: 好的！让我了解一些细节...
        1. 你打算使用什么原料？
        2. 对时间和设备有什么要求？

👤 你: 用水杨酸和乙酸酐，常规设备，2小时内完成

🤖 助手: 明白了！还需要确认：
        - 目标产量大约多少？
        - 是否需要提纯步骤？

👤 你: 10克左右，需要重结晶
```

### 3. 触发生成

```
👤 你: /generate

🚀 已提交生成任务（后台执行）
   任务ID: a1b2c3d4
   使用 /status 查看进度
   日志: logs/generation_tasks/a1b2c3d4/task.log
```

### 4. 系统自动提醒

```
======================================================================
⏸️  任务需要确认！
======================================================================
  任务ID: a1b2c3d4
  状态: awaiting_confirm

📋 需求已提取，文件路径:
  logs/generation_tasks/a1b2c3d4/requirements.json

💡 接下来可以:
  1. 查看需求: cat logs/generation_tasks/a1b2c3d4/requirements.json
  2. 修改需求: nano/vim logs/generation_tasks/a1b2c3d4/requirements.json
  3. 确认继续: /confirm
  4. 取消任务: /cancel
======================================================================
```

### 5. 查看和修改需求

```bash
# 在另一个终端中
cat logs/generation_tasks/a1b2c3d4/requirements.json

# 如果需要修改
vim logs/generation_tasks/a1b2c3d4/requirements.json
```

### 6. 确认继续

```
👤 你: /confirm

✅ 已确认需求，任务继续执行...
```

### 7. 查看结果

```
👤 你: /status

任务状态: ✅ COMPLETED
======================================================================
  任务ID: a1b2c3d4
  ...

✅ 任务完成!
  耗时: 8.35s
  Tokens: 3842

💡 查看方案:
  cat logs/generation_tasks/a1b2c3d4/plan.json
  /view a1b2c3d4

👤 你: /view a1b2c3d4

[显示格式化的实验方案]
```

## 所有命令

### 生成相关

- `/generate`, `/gen` - 触发生成任务（后台执行）
- `/status` - 查看当前任务状态
- `/confirm` - 确认需求，继续生成
- `/cancel` - 取消当前任务
- `/view <task_id>` - 查看生成的方案（格式化显示）
- `/tasks` - 列出所有任务

### 对话相关

- `/history` - 查看当前会话对话历史
- `/clear` - 清屏
- `/help` - 显示帮助
- `/quit`, `/exit` - 退出（任务继续运行）

## 独立检查工具

可以在新终端中运行，用于监控任务：

```bash
# 列出所有任务
python scripts/inspect_tasks.py --list

# 查看任务详情
python scripts/inspect_tasks.py --task a1b2c3d4

# 实时监控任务
python scripts/inspect_tasks.py --watch a1b2c3d4

# 查看日志（实时追踪）
python scripts/inspect_tasks.py --log a1b2c3d4

# 查看需求
python scripts/inspect_tasks.py --requirements a1b2c3d4

# 查看方案
python scripts/inspect_tasks.py --plan a1b2c3d4
```

## 文件结构

每个任务的数据存储在独立目录：

```
logs/generation_tasks/
├── a1b2c3d4/
│   ├── task.json          # 任务状态
│   ├── requirements.json  # 提取的需求 ⭐
│   ├── templates.json     # RAG检索结果
│   ├── plan.json         # 生成的方案 ⭐
│   └── task.log          # 执行日志
├── b2c3d4e5/
│   └── ...
└── .worker.lock          # 工作线程锁
```

## 工作线程管理

### 自动启动

首次运行CLI时，系统会自动启动工作线程：

```
[TaskManager] Worker线程已启动 (daemon=False, pid=12345)
```

### 多实例检测

如果已有工作线程在运行，新CLI会检测到：

```
[TaskManager] Worker已在其他进程运行，跳过启动
```

### 空闲超时

工作线程在5分钟无活动后自动退出：

```
[TaskWorker] 空闲超时，自动退出
```

### 优雅关闭

- 捕获 SIGTERM、SIGINT 信号
- 使用 atexit 清理资源
- 释放文件锁

## 常见问题

### 1. 任务卡在 AWAITING_CONFIRM 状态

**原因**：等待用户确认需求。

**解决**：
- 使用 `/status` 查看需求文件路径
- 查看并修改需求（如需要）
- 使用 `/confirm` 确认继续

### 2. CLI退出后任务会停止吗？

**不会**。工作线程是非守护线程，CLI退出后会继续运行。

可以：
- 重新启动CLI查看状态
- 使用独立检查工具监控

### 3. 如何查看任务日志？

方法1：直接查看文件
```bash
cat logs/generation_tasks/<task_id>/task.log
```

方法2：使用检查工具（实时追踪）
```bash
python scripts/inspect_tasks.py --log <task_id>
```

### 4. 如何手动修改需求？

```bash
# 查看需求
cat logs/generation_tasks/<task_id>/requirements.json

# 修改需求
nano logs/generation_tasks/<task_id>/requirements.json

# 返回CLI确认
/confirm
```

### 5. 工作线程如何销毁？

工作线程会在以下情况自动销毁：
- 空闲超时（5分钟无活动）
- 收到 SIGTERM/SIGINT 信号
- 程序正常退出

### 6. 如何强制停止工作线程？

```bash
# 查找工作线程进程
ps aux | grep TaskWorker

# 发送SIGTERM信号（优雅关闭）
kill <pid>

# 如果不响应，发送SIGKILL
kill -9 <pid>
```

## 最佳实践

### 1. 明确描述需求

与Chatbot对话时，尽量明确：
- 目标化合物
- 原料和设备
- 时间和成本约束
- 特殊要求

### 2. 检查需求文件

在确认前，务必查看 `requirements.json`，确保提取正确。

### 3. 保持CLI连接

虽然任务可以后台运行，但保持CLI连接可以及时收到提醒。

### 4. 使用多终端

- 终端1：运行主CLI，与Chatbot对话
- 终端2：使用检查工具监控任务
- 终端3：查看/编辑需求文件

### 5. 定期清理

任务文件会累积，定期清理旧任务：

```bash
# 查看所有任务
python scripts/inspect_tasks.py --list

# 手动删除旧任务目录
rm -rf logs/generation_tasks/<old_task_id>
```

## 故障排查

### 日志位置

- 任务日志：`logs/generation_tasks/<task_id>/task.log`
- 工作线程锁：`logs/generation_tasks/.worker.lock`

### 检查工作线程状态

```bash
# 方法1：查看锁文件
cat logs/generation_tasks/.worker.lock

# 方法2：查看进程
ps aux | grep TaskWorker
```

### 重置系统

如果遇到问题，可以完全重置：

```bash
# 停止所有工作线程
pkill -f TaskWorker

# 删除所有任务数据
rm -rf logs/generation_tasks/*

# 重新启动
python examples/workflow_cli.py
```

## 下一步

- [ ] 实现RAG模板检索
- [ ] 添加方案评估反馈
- [ ] 支持多轮方案迭代
- [ ] 添加方案导出功能（Markdown/PDF）
- [ ] 集成Reflector和Curator（完整ACE循环）
