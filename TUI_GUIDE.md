# TUI 使用指南

## 启动TUI

```bash
conda activate OntologyConstruction
python examples/workflow_tui.py
```

## 界面布局

```
┌────────────────────────────────────────────────────────────┐
│  Header - 标题栏                                           │
├──────────┬──────────────────┬──────────────────────────────┤
│ 📋任务列表│ 💬 对话区        │ 📊 任务详情                  │
│ (25%)    │ (45%)            │ (30%)                        │
│          │                  │                              │
│ 实时更新 │ 流式聊天         │ 点击任务查看                 │
│ 每2秒    │ 支持斜杠命令     │ 详细信息                     │
├──────────┴──────────────────┴──────────────────────────────┤
│ 🔧 系统日志 (20%)                                          │
│ - MOSES初始化状态                                          │
│ - 任务事件                                                 │
│ - 错误信息                                                 │
└────────────────────────────────────────────────────────────┘
```

## 主要功能

### 1. 对话交互
- 在中间对话区输入框输入消息
- 支持流式响应（逐字显示）
- 自动保存对话历史

### 2. 任务管理
- **左侧任务列表**自动刷新（每2秒检测文件变化）
- **点击任务**查看详细信息（右侧面板）
- 支持的任务状态：
  - ⏳ pending - 待处理
  - 🔍 extracting - 提取需求中
  - ⏸️ awaiting_confirm - 等待确认
  - 📚 retrieving - 检索模板中
  - ⚙️ generating - 生成中
  - ✅ completed - 已完成
  - ❌ failed - 失败
  - 🚫 cancelled - 已取消

### 3. 文本复制功能 ⭐

TUI保持了鼠标支持（用于点击任务、滚动等），同时支持文本选择和复制。

#### 复制方法：Shift+鼠标

```
1. 按住 Shift 键
2. 鼠标拖动选择文本（绕过TUI应用的鼠标捕获）
3. 复制（取决于你的终端）:
   • Linux终端: Ctrl+Shift+C
   • macOS iTerm2/Terminal: Cmd+C
   • Windows Terminal: 鼠标右键 → 复制
```

**工作原理**：
- TUI默认启用鼠标支持（`mouse=True`），鼠标点击和拖动会被应用捕获
- 按住 `Shift` 键可以绕过应用捕获，将鼠标事件传递给终端
- 终端接收到鼠标事件后，会进行文本选择（终端原生功能）

**无需Tab聚焦**：
- 直接 `Shift+鼠标拖动` 即可，不需要先按Tab切换焦点
- Tab键用于在UI组件间导航（如输入框、任务列表）

#### 终端兼容性

| 终端 | Shift+鼠标 | 复制快捷键 | 备注 |
|------|-----------|-----------|------|
| GNOME Terminal | ✅ | Ctrl+Shift+C | 完全支持 |
| iTerm2 (macOS) | ✅ | Cmd+C | 完全支持 |
| macOS Terminal | ✅ | Cmd+C | 完全支持 |
| Windows Terminal | ✅ | Ctrl+Shift+C 或右键 | 完全支持 |
| Konsole | ✅ | Ctrl+Shift+C | 完全支持 |
| Alacritty | ✅ | Ctrl+Shift+C | 完全支持 |
| xterm | ⚠️  | 有限支持 | 建议用现代终端 |

#### 备用方案：直接访问日志文件

如果你的终端不支持Shift+鼠标（极少见），可以直接查看日志文件：

```bash
# 任务日志（子进程的输出）
cat logs/generation_tasks/<task_id>/task.log

# 快速复制到剪贴板
cat logs/generation_tasks/<task_id>/task.log | xclip -selection clipboard  # Linux
cat logs/generation_tasks/<task_id>/task.log | pbcopy  # macOS

# 或在TUI中使用 /logs 命令查看后，再访问文件
```

**系统日志说明**：
- TUI的系统日志面板（底部）只在内存中，没有对应的日志文件
- 如需保存系统日志，可以使用终端的输出重定向功能

### 3. 斜杠命令

```bash
# 生成任务
/generate     # 根据对话历史生成实验方案

# 任务操作
/confirm      # 确认需求，继续生成
/cancel       # 取消当前任务
/view <id>    # 查看生成的方案
/logs <id>    # 查看任务日志

# 信息查询
/tasks        # 列出当前会话的所有任务
/history      # 查看对话历史
/help         # 显示帮助

# 其他
/quit, q      # 退出（任务继续在后台运行）
```

### 4. 快捷键

```
鼠标操作:
  点击任务          - 查看任务详情
  Shift+鼠标拖动    - 选择文本（然后Ctrl+Shift+C复制）
  鼠标滚轮          - 滚动日志面板

键盘:
  Tab / Shift+Tab   - 在面板间切换焦点（用于输入框导航）
  F1                - 显示帮助
  Ctrl+L            - 清空对话区
  Ctrl+C, q         - 退出
```

## 工作流程示例

### 典型流程

```
1. 启动TUI → 系统初始化（约5秒）

2. 描述需求：
   你: 我想合成阿司匹林
   助手: 好的！让我了解一些细节...
   你: 用水杨酸和乙酸酐，2小时内完成

3. 生成方案：
   你: /generate
   系统: ✅ 已提交生成任务 abc123

4. 观察进度：
   - 左侧任务列表显示：🔍 abc123 [extracting]
   - 几秒后变为：⏸️ abc123 [awaiting_confirm]
   - 点击任务查看详情

5. 确认需求：
   你: /confirm
   系统: ✅ 任务已确认，继续生成...

6. 等待完成：
   - 状态变化：📚 retrieving → ⚙️ generating → ✅ completed
   - 可以使用 /logs abc123 查看实时日志

7. 查看方案：
   你: /view abc123
   系统: 显示格式化的实验方案
```

## 技术特性

### 1. 智能缓存刷新
- TaskManager自动检测 `task.json` 文件修改时间
- 只在文件变化时重新加载（性能优化）
- 无需手动刷新，始终显示最新状态

### 2. 会话隔离
- 每次启动TUI创建新会话ID
- 只显示当前会话的任务（界面简洁）
- 历史会话的任务不会显示

### 3. 后台初始化
- MOSES在后台线程初始化（不阻塞UI）
- 系统日志实时显示初始化进度
- 初始化完成后自动显示摘要

### 4. stdout隔离
- TUI使用textual渲染（不依赖stdout）
- MOSES后台线程可以自由重定向stdout到日志文件
- 完全避免了stdout竞态条件

## 常见问题

### Q: 任务列表不更新？
A: 检查任务文件是否存在：`ls logs/generation_tasks/`

### Q: MOSES初始化很慢？
A: 正常，第一次加载大型本体可能需要几分钟。可以在系统日志面板查看进度。

### Q: 退出后任务还在运行吗？
A: 是的！任务在独立子进程中运行，TUI退出不影响任务执行。可以通过查看 `logs/generation_tasks/<task_id>/task.json` 确认。

### Q: 如何恢复之前的任务？
A: 当前会话只显示本次创建的任务。如需查看历史任务，可以直接查看文件系统或使用CLI工具。

## 开发参考

### 给Web工程师的接入示例

TUI展示了如何使用业务组件，Web后端可以类似调用：

```python
# FastAPI示例
from fastapi import FastAPI
from workflow.task_scheduler import TaskScheduler
from workflow.task_manager import get_task_manager
from chatbot.chatbot import Chatbot

app = FastAPI()
scheduler = TaskScheduler()
task_manager = get_task_manager()

@app.get("/api/tasks")
def get_tasks(session_id: str):
    # 直接复用业务逻辑
    tasks = task_manager.get_session_tasks(session_id)
    return [task.to_dict() for task in tasks]

@app.post("/api/tasks")
def create_task(session_id: str, history: list):
    task_id = scheduler.submit_task(session_id, history)
    return {"task_id": task_id}

@app.get("/api/tasks/{task_id}/logs")
def get_logs(task_id: str, tail: int = 50):
    logs = scheduler.get_logs(task_id, tail)
    return {"logs": logs}
```

## 下一步

- [ ] 添加任务进度条（生成阶段）
- [ ] 支持任务搜索/过滤
- [ ] 添加快捷键导航
- [ ] 支持主题切换
- [ ] 导出方案为PDF/Markdown

