# 会话管理快速开始

## 🚀 5分钟快速体验

### 步骤1: 查看当前模式

```bash
# 启动CLI
conda activate OntologyConstruction
python examples/workflow_cli.py
```

默认是**内存模式**，你会看到：
```
💡 当前使用内存模式，会话不会持久化
   修改 configs/chatbot_config.yaml 中的 memory.type 为 'sqlite' 以启用会话管理
```

### 步骤2: 测试基本命令（内存模式）

```
👤 你: /help             # 查看所有命令
👤 你: /sessions         # 内存模式下返回空列表
👤 你: /new test1        # 创建新会话
👤 你: 你好               # 开始对话
👤 你: /history          # 查看历史
👤 你: /quit             # 退出
```

**重新启动**：
```bash
python examples/workflow_cli.py
```

你会发现之前的对话**已丢失**（内存模式特性）。

---

### 步骤3: 切换到SQLite模式

编辑 `configs/chatbot_config.yaml`:

```yaml
chatbot:
  memory:
    type: "sqlite"  # 改这一行（原来是 in_memory）
    sqlite_path: "data/chatbot_memory.db"
```

保存后重启CLI：
```bash
python examples/workflow_cli.py
```

现在你会看到：
```
📌 已创建新会话: 20251027_1137_abc123
```

---

### 步骤4: 测试会话持久化

**第一次运行**：
```
👤 [abc123] 你: 我想合成阿司匹林
🤖 助手: 好的！...
👤 [abc123] 你: /history
[显示对话历史]
👤 [abc123] 你: /quit
```

**第二次运行**（模拟重启）：
```bash
python examples/workflow_cli.py
```

你会看到：
```
📦 检测到 1 个历史会话
   使用 /sessions 查看所有会话
📌 当前会话: 20251027_1137_abc123  # 自动恢复！
```

```
👤 [abc123] 你: /history
[显示之前的对话，内容保留！]
```

---

### 步骤5: 多会话管理

```
👤 [abc123] 你: /sessions
==================================================
所有会话列表
==================================================

👉 20251027_1137_abc123
   消息数: 4
   预览: 我想合成阿司匹林...

👤 [abc123] 你: /new aspirin_project
✅ 已创建新会话: aspirin_project

👤 [aspirin] 你: 这是一个新的会话
🤖 助手: ...

👤 [aspirin] 你: /sessions
==================================================
所有会话列表
==================================================

   20251027_1137_abc123
   消息数: 4

👉 aspirin_project
   消息数: 2

👤 [aspirin] 你: /switch 20251027_1137_abc123
✅ 已切换到会话: 20251027_1137_abc123

👤 [abc123] 你: /history
[显示原来会话的历史]
```

---

## 🎯 实际使用示例

### 示例1: 多项目并行研发

```yaml
# configs/chatbot_config.yaml
memory:
  type: "sqlite"
```

```
# 项目A：阿司匹林合成
👤 你: /new aspirin_synthesis
👤 [aspirin] 你: 我想用水杨酸合成阿司匹林
👤 [aspirin] 你: /generate
[生成任务ID: task_001]

# 项目B：青霉素研究
👤 [aspirin] 你: /new penicillin_research
👤 [penicillin] 你: 我需要研究青霉素的合成路线
👤 [penicillin] 你: /generate
[生成任务ID: task_002]

# 回到项目A查看结果
👤 [penicillin] 你: /switch aspirin_synthesis
👤 [aspirin] 你: /view task_001
[查看阿司匹林方案]

# 第二天：继续项目A
$ python examples/workflow_cli.py
📦 检测到 2 个历史会话
👤 [penicillin] 你: /sessions
👤 [penicillin] 你: /switch aspirin_synthesis
👤 [aspirin] 你: /history
[回顾昨天的讨论]
```

---

### 示例2: 临时测试（内存模式）

```yaml
# configs/chatbot_config.yaml
memory:
  type: "in_memory"
```

```
# 快速测试新功能
👤 你: 帮我测试一下MOSES查询
👤 你: /quit  # 退出后不保存历史
```

**优点**：
- 启动快（无需读取数据库）
- 不占用磁盘空间
- 适合快速测试

---

## 📋 命令速查卡

### 会话管理
| 命令 | 说明 | 示例 |
|------|------|------|
| `/sessions` | 列出所有会话 | `/sessions` |
| `/switch <id>` | 切换会话 | `/switch aspirin_project` |
| `/new [name]` | 创建新会话 | `/new my_project` |
| `/history` | 查看当前会话历史 | `/history` |

### 任务管理
| 命令 | 说明 | 示例 |
|------|------|------|
| `/generate` | 生成实验方案 | `/generate` |
| `/status` | 查看任务状态 | `/status` |
| `/tasks` | 列出所有任务 | `/tasks` |
| `/view <id>` | 查看方案 | `/view abc123` |

### 其他
| 命令 | 说明 | 示例 |
|------|------|------|
| `/help` | 显示帮助 | `/help` |
| `/clear` | 清屏（不删除历史） | `/clear` |
| `/quit` | 退出 | `/quit` |

---

## 🔧 配置模板

### 内存模式（默认）
```yaml
# configs/chatbot_config.yaml
chatbot:
  llm:
    provider: "qwen"
    model_name: "qwen-plus"
    temperature: 0.7
    max_tokens: 4096
    enable_thinking: true

  moses:
    max_workers: 4
    query_timeout: 600

  memory:
    type: "in_memory"  # 内存模式

  system_prompt: |
    你是一个专业的化学实验助手...
```

### SQLite模式（推荐）
```yaml
# configs/chatbot_config.yaml
chatbot:
  llm:
    provider: "qwen"
    model_name: "qwen-plus"
    temperature: 0.7
    max_tokens: 4096
    enable_thinking: true

  moses:
    max_workers: 4
    query_timeout: 600

  memory:
    type: "sqlite"  # SQLite模式
    sqlite_path: "data/chatbot_memory.db"  # 数据库路径

  system_prompt: |
    你是一个专业的化学实验助手...
```

---

## ❓ 常见问题

### Q1: 如何查看保存了哪些会话？

**A**: 使用 `/sessions` 命令（仅SQLite模式）

### Q2: 可以删除旧会话吗？

**A**: 目前需要手动操作数据库：
```bash
sqlite3 data/chatbot_memory.db "DELETE FROM checkpoints WHERE thread_id = 'old_session';"
```

未来版本会添加 `/delete <session_id>` 命令。

### Q3: 内存模式能否列出会话？

**A**: 不能。内存模式不支持 `/sessions` 命令，会提示切换到SQLite模式。

### Q4: 切换模式后原来的会话怎么办？

**A**:
- 内存→SQLite：原来的会话丢失（内存模式不持久化）
- SQLite→内存：数据库文件保留，切回SQLite后可恢复

### Q5: 数据库文件在哪里？

**A**: 默认路径 `data/chatbot_memory.db`（可在配置中修改）

---

## 📚 完整文档

详细说明请参考：[SESSION_MANAGEMENT.md](./SESSION_MANAGEMENT.md)

包含：
- 技术细节
- 故障排除
- 最佳实践
- API参考
