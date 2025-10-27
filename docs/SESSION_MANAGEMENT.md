# 会话管理功能指南

## 概述

Workflow CLI 现在支持完整的会话管理功能，允许用户：
- ✅ 创建和切换多个独立会话
- ✅ 在内存模式和SQLite持久化模式之间切换
- ✅ 恢复历史会话（SQLite模式）
- ✅ 查看会话列表和历史记录

---

## 两种模式对比

| 功能 | 内存模式 | SQLite模式 |
|------|---------|-----------|
| 会话持久化 | ❌ 程序退出后丢失 | ✅ 永久保存 |
| 多会话管理 | ✅ 支持 | ✅ 支持 |
| 历史会话恢复 | ❌ 不支持 | ✅ 支持 |
| 会话列表查询 | ❌ 不支持 | ✅ 支持 |
| 适用场景 | 快速测试、临时对话 | 长期项目、需要保存历史 |

---

## 模式切换

### 方法1：修改配置文件

编辑 `configs/chatbot_config.yaml`:

```yaml
chatbot:
  memory:
    type: "sqlite"  # 改为sqlite启用持久化（默认为in_memory）
    sqlite_path: "data/chatbot_memory.db"
```

### 方法2：查看当前模式

启动CLI时会自动提示当前模式：

```
内存模式：
💡 当前使用内存模式，会话不会持久化
   修改 configs/chatbot_config.yaml 中的 memory.type 为 'sqlite' 以启用会话管理

SQLite模式（首次使用）：
📌 已创建新会话: 20251027_1130_abc123

SQLite模式（检测到历史会话）：
📦 检测到 3 个历史会话
   使用 /sessions 查看所有会话
   使用 /switch <session_id> 切换会话
📌 当前会话: 20251027_1130_abc123
```

---

## 会话管理命令

### 1. `/sessions` - 列出所有会话

**仅SQLite模式可用**

```
👤 你: /sessions

==================================================
所有会话列表
==================================================

👉 20251027_1130_abc123
   消息数: 15
   预览: 我想合成阿司匹林...

   20251026_0930_def456
   消息数: 8
   预览: 如何合成青霉素...

💡 使用 /switch <session_id> 切换会话
   使用 /new [name] 创建新会话
```

**内存模式**：
```
暂无保存的会话
提示: 当前使用内存模式，会话不会持久化
      修改 configs/chatbot_config.yaml 中的 memory.type 为 'sqlite' 以启用持久化
```

---

### 2. `/switch <session_id>` - 切换会话

```
👤 你: /switch 20251026_0930_def456

✅ 已切换到会话: 20251026_0930_def456
   历史消息: 8 条
   使用 /history 查看历史记录
```

**错误处理**（SQLite模式）：
```
👤 你: /switch nonexistent_session

❌ 会话 nonexistent_session 不存在
可用会话: 20251027_1130_abc123, 20251026_0930_def456
```

**内存模式**：
- 可以切换到任意会话ID（即使不存在）
- 切换后会开始一个新的空会话

---

### 3. `/new [session_name]` - 创建新会话

**自动生成ID**：
```
👤 你: /new

✅ 已创建新会话: 20251027_1145_xyz789
```

**自定义名称**：
```
👤 你: /new aspirin_synthesis

✅ 已创建新会话: aspirin_synthesis
```

**重名处理**（SQLite模式）：
```
👤 你: /new aspirin_synthesis

❌ 会话 aspirin_synthesis 已存在
   请使用其他名称或使用 /switch aspirin_synthesis
```

---

### 4. `/history` - 查看当前会话历史

```
👤 你: /history

======================================================================
会话历史:
======================================================================

[1] 👤 你:
我想合成阿司匹林
----------------------------------------------------------------------

[2] 🤖 助手:
好的！让我了解一些细节。请问您需要合成的量是多少？
----------------------------------------------------------------------

[3] 👤 你:
100g就够了
----------------------------------------------------------------------
```

---

## 会话ID格式

### 自动生成格式

```
YYYYMMDD_HHMM_<6位UUID>
```

**示例**：
- `20251027_1130_abc123`
- `20251026_0930_def456`

**优点**：
- 按时间排序
- 唯一性保证
- 易于识别创建时间

### 自定义格式

用户可以使用任意字符串作为会话ID：

```
aspirin_synthesis
penicillin_project_v2
test_session_001
```

**建议**：
- 使用小写字母、数字、下划线
- 避免空格和特殊字符
- 使用有意义的名称

---

## 提示符显示

### SQLite模式

显示当前会话的简化ID（最后6位）：

```
👤 [abc123] 你:
```

### 内存模式

不显示会话ID：

```
👤 你:
```

---

## 使用场景

### 场景1: 单个临时任务（内存模式）

```yaml
# configs/chatbot_config.yaml
memory:
  type: "in_memory"
```

```
# 启动CLI
$ python examples/workflow_cli.py

👤 你: 我想合成阿司匹林
🤖 助手: ...
👤 你: /generate
👤 你: /quit  # 退出后历史丢失
```

---

### 场景2: 多个并行项目（SQLite模式）

```yaml
# configs/chatbot_config.yaml
memory:
  type: "sqlite"
  sqlite_path: "data/chatbot_memory.db"
```

```
# 第一天
$ python examples/workflow_cli.py

👤 你: /new aspirin_project
✅ 已创建新会话: aspirin_project

👤 [aspirin] 你: 我想合成阿司匹林
🤖 助手: ...
👤 [aspirin] 你: /generate
👤 [aspirin] 你: /quit

# 第二天（恢复项目）
$ python examples/workflow_cli.py

📦 检测到 1 个历史会话
📌 当前会话: aspirin_project

👤 [aspirin] 你: /history  # 查看昨天的对话
👤 [aspirin] 你: 继续讨论...

# 创建新项目
👤 [aspirin] 你: /new penicillin_project
✅ 已创建新会话: penicillin_project

👤 [penicillin] 你: 我想合成青霉素
...

# 切换回第一个项目
👤 [penicillin] 你: /switch aspirin_project
✅ 已切换到会话: aspirin_project
```

---

### 场景3: 长期研究项目（SQLite模式 + 任务管理）

```
# 第一周
👤 你: /new long_term_research
👤 [long_term] 你: 我需要研究一系列化合物
🤖 助手: ...
👤 [long_term] 你: /generate
[任务ID: task_001]

# 第二周
👤 [long_term] 你: /view task_001  # 查看上周的方案
👤 [long_term] 你: 根据上周的结果，我想改进第3步
🤖 助手: ...
👤 [long_term] 你: /generate
[任务ID: task_002]

# 第三周
👤 [long_term] 你: /tasks  # 查看所有生成的方案
👤 [long_term] 你: /history  # 回顾整个研究过程
```

---

## 数据存储

### 内存模式

- **存储位置**：进程内存
- **生命周期**：程序运行期间
- **大小限制**：受系统内存限制

### SQLite模式

- **存储位置**：`data/chatbot_memory.db`（可配置）
- **生命周期**：永久（直到手动删除）
- **大小限制**：无限制（SQLite支持TB级数据）

**数据库结构**（LangGraph自动管理）：

```sql
CREATE TABLE checkpoints (
    thread_id TEXT,        -- 会话ID
    checkpoint_id TEXT,    -- 检查点ID
    parent_id TEXT,        -- 父检查点
    checkpoint BLOB,       -- 序列化的会话状态（包含消息历史）
    metadata TEXT,         -- 元数据
    PRIMARY KEY (thread_id, checkpoint_id)
);
```

---

## 故障排除

### 问题1: `/sessions` 返回空列表

**原因**：
- 当前使用内存模式
- 或SQLite数据库为空

**解决**：
1. 检查配置：`configs/chatbot_config.yaml`
2. 确认 `memory.type` 为 `"sqlite"`
3. 重启CLI

---

### 问题2: SQLite模式下会话未持久化

**原因**：
- 数据库文件路径错误
- 权限不足

**解决**：
1. 检查 `sqlite_path` 配置
2. 确保目录存在且有写权限：
   ```bash
   mkdir -p data
   chmod 755 data
   ```

---

### 问题3: 切换会话后历史为空

**可能原因**：
1. 内存模式下切换到未使用的会话ID
2. SQLite数据库损坏

**解决**：
- 内存模式：这是正常行为，新会话从空白开始
- SQLite模式：
  ```bash
  # 检查数据库
  sqlite3 data/chatbot_memory.db "SELECT DISTINCT thread_id FROM checkpoints;"
  ```

---

## 最佳实践

### 1. 会话命名规范

**推荐**：
```
aspirin_synthesis_v1
project_20251027
experiment_batch_01
```

**避免**：
```
test
session
abc
```

### 2. 定期清理旧会话（SQLite模式）

手动删除数据库文件：
```bash
# 备份
cp data/chatbot_memory.db data/chatbot_memory.db.backup

# 删除特定会话
sqlite3 data/chatbot_memory.db "DELETE FROM checkpoints WHERE thread_id = 'old_session';"

# 或删除整个数据库重新开始
rm data/chatbot_memory.db
```

### 3. 备份重要会话

```bash
# 导出整个数据库
cp data/chatbot_memory.db ~/backups/chatbot_memory_$(date +%Y%m%d).db

# 或使用git版本控制
git add data/chatbot_memory.db
git commit -m "Backup important research sessions"
```

---

## 技术细节

### 会话状态结构

每个会话的状态包含：
```python
{
    "messages": [
        {"role": "user", "content": "..."},
        {"role": "assistant", "content": "..."},
        # ...
    ],
    # 其他LangGraph状态（工具调用记录等）
}
```

### 会话ID生成算法

```python
def generate_session_id(custom_name: str = None) -> str:
    if custom_name:
        return custom_name
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        short_id = str(uuid.uuid4())[:6]
        return f"{timestamp}_{short_id}"
```

### 列出会话实现（SQLite模式）

```python
def list_sessions(self) -> List[str]:
    conn = self.checkpointer.conn
    cursor = conn.execute("SELECT DISTINCT thread_id FROM checkpoints")
    return [row[0] for row in cursor.fetchall()]
```

---

## 相关命令速查

| 命令 | 功能 | 模式 |
|------|------|------|
| `/sessions` | 列出所有会话 | SQLite |
| `/switch <id>` | 切换会话 | 通用 |
| `/new [name]` | 创建新会话 | 通用 |
| `/history` | 查看当前会话历史 | 通用 |
| `/clear` | 清屏（不删除历史） | 通用 |

---

## 更新日志

### v0.2 (2025-10-27)
- ✅ 添加会话管理功能
- ✅ 支持SQLite持久化
- ✅ 添加 `/sessions`, `/switch`, `/new` 命令
- ✅ 启动时自动检测历史会话
- ✅ 在提示符中显示会话ID

### v0.1 (2025-10-25)
- ✅ 基础Chatbot功能
- ✅ 任务生成和管理
- ✅ 内存会话支持
