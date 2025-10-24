# Chatbot 使用文档

## 📋 概述

化学实验助手Chatbot基于LangGraph的`create_react_agent`预制组件构建，提供：
- ✅ 自动调用MOSES本体查询工具
- ✅ 对话记忆管理（内存/SQLite双模式）
- ✅ 流式响应（实时打字效果）
- ✅ 使用qwen-plus模型（支持thinking功能）

## 🎯 项目结构

```
src/chatbot/
├── __init__.py          # 导出接口
├── chatbot.py           # 主Chatbot类（~200行）
├── tools.py             # MOSES工具封装
└── config.py            # 配置加载

configs/
└── chatbot_config.yaml  # Chatbot配置

examples/
└── chatbot_cli.py       # CLI交互示例（可执行）
```

**代码量**: 仅~100行核心代码（vs 手动实现300+行）

## 🚀 快速开始

### 1. 环境准备

使用conda环境：
```bash
conda activate OntologyConstruction
```

### 2. 配置API密钥

在`.env`文件中添加：
```bash
# Qwen API密钥（必需）
DASHSCOPE_API_KEY=your_dashscope_api_key_here
```

或导出环境变量：
```bash
export DASHSCOPE_API_KEY="your_key_here"
```

### 3. 配置记忆模式

编辑`configs/chatbot_config.yaml`:

**开发调试（内存模式）**：
```yaml
chatbot:
  memory:
    type: "in_memory"  # 会话结束后记录丢失，无需数据库
```

**生产使用（持久化模式）**：
```yaml
chatbot:
  memory:
    type: "sqlite"  # 可恢复历史会话
    sqlite_path: "data/chatbot_memory.db"
```

> **注意**: SQLite模式需要安装额外包（见依赖部分）

### 4. 运行CLI交互

```bash
# 方式1：直接运行
python examples/chatbot_cli.py

# 方式2：使用conda run
conda run -n OntologyConstruction python examples/chatbot_cli.py
```

## 💻 编程接口

### 基本用法

```python
from src.chatbot import Chatbot

# 初始化
bot = Chatbot(config_path="configs/chatbot_config.yaml")

# 单轮对话
response = bot.chat("什么是奎宁？")
print(response)

# 清理资源
bot.cleanup()
```

### 多轮对话（自动记忆）

```python
session_id = "user_123"

# 第一轮
response1 = bot.chat("什么是奎宁？", session_id=session_id)
print(response1)

# 第二轮（会记住上下文）
response2 = bot.chat("它有什么用途？", session_id=session_id)
print(response2)
```

### 流式响应（实时打字效果）

```python
print("助手: ", end="", flush=True)

full_response = ""
for chunk in bot.stream_chat("解释电化学传感器", session_id="user_456"):
    # 只打印新增部分
    if chunk.startswith(full_response):
        new_part = chunk[len(full_response):]
        print(new_part, end="", flush=True)
        full_response = chunk

print()  # 换行
```

### 查看历史

```python
history = bot.get_history(session_id="user_123")

for msg in history:
    print(f"{msg['role']}: {msg['content']}")
```

## 🔧 配置说明

### `configs/chatbot_config.yaml`

```yaml
chatbot:
  # LLM配置
  llm:
    provider: "qwen"
    model_name: "qwen-plus"      # qwen-plus具有thinking功能
    temperature: 0.7              # 控制随机性
    max_tokens: 4096              # 最大输出长度
    enable_thinking: true         # qwen-plus特性

  # MOSES工具配置
  moses:
    max_workers: 4                # QueryManager并发线程数
    query_timeout: 30             # 查询超时（秒），可调整

  # 记忆配置
  memory:
    type: "in_memory"             # "in_memory" | "sqlite"
    sqlite_path: "data/chatbot_memory.db"  # SQLite模式使用

  # 系统提示词（可自定义）
  system_prompt: |
    你是一个专业的化学实验助手...
```

## 📦 依赖安装

### 必需依赖（已在环境中）

```bash
pip install langchain>=0.3.7
pip install langchain-community>=0.3.0
pip install langchain-core>=0.3.0
pip install langgraph>=0.2.45
pip install dashscope>=1.14.0  # Qwen API客户端
pip install pyyaml pydantic
```

### 可选依赖（SQLite持久化）

如果需要持久化记忆：

```bash
pip install langgraph-checkpoint-sqlite
```

> 如果不安装，系统会自动降级到内存模式并给出提示

## 🎮 CLI命令

运行`python examples/chatbot_cli.py`后可用的命令：

| 命令 | 功能 |
|------|------|
| `help` | 显示帮助信息 |
| `history` | 查看当前会话历史 |
| `clear` | 清屏 |
| `quit` / `exit` / `q` | 退出程序 |

## 🧪 测试

### 基本功能测试

```bash
# 测试配置加载、初始化、简单对话
conda run -n OntologyConstruction env PYTHONPATH=. \
  python scripts/test/test_chatbot_basic.py
```

**测试结果示例**：
```
============================================================
测试1: 配置加载
============================================================
✅ 配置文件加载成功
  - LLM模型: qwen-plus
  - 记忆类型: in_memory
  - MOSES超时: 30秒
✅ 配置验证通过
```

## 🔍 工作原理

### 核心组件：LangGraph `create_react_agent`

```python
self.agent = create_react_agent(
    model=self.llm,                    # qwen-plus LLM
    tools=[moses_tool],                # MOSES本体查询工具
    checkpointer=self.checkpointer,    # 记忆管理器
    prompt="你是专业的化学实验助手"
)
```

**一行代码完成**：
- 工具调用逻辑（ReAct模式）
- 消息状态管理
- 对话记忆持久化

### 工具调用流程

```
用户输入 → Agent判断 → 需要查询本体？
                           ↓ 是
                    调用MOSES Tool
                           ↓
                    QueryManager.submit_query()
                           ↓
                    LangGraph workflow处理
                           ↓
                    返回格式化结果
                           ↓
                    Agent整合回复 → 用户
```

### 记忆管理

**内存模式**（MemorySaver）：
- 优点：无需数据库，简单快速
- 缺点：程序重启后丢失
- 适用：开发调试

**SQLite模式**（SqliteSaver）：
- 优点：持久化存储，可恢复历史
- 缺点：需要额外依赖
- 适用：生产环境

通过`thread_id`隔离不同用户/会话。

## ⚠️ 常见问题

### 1. 缺少DASHSCOPE_API_KEY

**错误**：
```
ValidationError: Did not find dashscope_api_key
```

**解决**：
```bash
export DASHSCOPE_API_KEY="your_key_here"
# 或在.env文件中配置
```

### 2. SQLite不可用

**提示**：
```
[Chatbot] ⚠️  SQLite checkpointer不可用，降级为内存模式
```

**解决**（可选）：
```bash
pip install langgraph-checkpoint-sqlite
```

或直接使用内存模式（修改配置为`type: "in_memory"`）

### 3. MOSES查询超时

**错误**：
```
本体查询超时（30秒）
```

**解决**：
在`configs/chatbot_config.yaml`中增加超时时间：
```yaml
chatbot:
  moses:
    query_timeout: 60  # 改为60秒
```

### 4. 导入错误

**错误**：
```
ModuleNotFoundError: No module named 'src'
```

**解决**：
使用`PYTHONPATH`运行：
```bash
PYTHONPATH=. python examples/chatbot_cli.py
```

## 🎯 与其他系统集成

### 在ACE框架中使用

```python
# 在ACE Generator中调用Chatbot获取结构化需求
from src.chatbot import Chatbot

class ACEGenerator:
    def __init__(self):
        self.chatbot = Chatbot()

    def extract_requirements(self, user_input: str) -> dict:
        # 使用chatbot提取需求
        response = self.chatbot.chat(user_input)
        # 解析response为结构化数据...
        return structured_requirements
```

### Web API封装（未来扩展）

```python
from fastapi import FastAPI
from src.chatbot import Chatbot

app = FastAPI()
bot = Chatbot()

@app.post("/chat")
async def chat_endpoint(message: str, session_id: str):
    response = bot.chat(message, session_id=session_id)
    return {"response": response}
```

## 📊 性能优化建议

1. **MOSES预加载**: QueryManager在首次调用时才初始化本体（延迟加载），避免启动慢

2. **并发控制**: 调整`max_workers`适应服务器性能
   ```yaml
   moses:
     max_workers: 8  # 更多并发
   ```

3. **缓存**: MOSES内置查询缓存，相同问题重复查询会很快

4. **流式响应**: CLI使用流式响应提升用户体验

## 📝 示例对话

```
👤 你: 什么是指示剂置换分析法？

🤖 助手: [调用MOSES查询本体...]

指示剂置换分析法（Indicator Displacement Assay, IDA）是一种基于主客体识别的传感策略。
工作原理是：首先将指示剂分子与受体（host）结合形成复合物，当待测分析物（analyte）存在时，
由于其与受体有更高的结合亲和力，会竞争性地置换出指示剂，导致可检测的信号变化...

👤 你: 它在电化学传感器中如何应用？

🤖 助手: [记住上下文，继续回答...]

在电化学传感器中，IDA的应用包括使用beta-环糊精作为受体，亚甲基蓝作为指示剂...
```

## 🚧 已知限制

1. **SQLite多进程**: SQLite模式不支持多进程并发写入
2. **工具扩展**: 当前仅集成MOSES，未来可添加更多工具（RAG、计算器等）
3. **流式粒度**: 流式响应是按完整消息块，不是token级别

## 📚 参考资源

- [LangGraph官方文档](https://langchain-ai.github.io/langgraph/)
- [create_react_agent API](https://langchain-ai.github.io/langgraph/agents/agents/)
- [Qwen API文档](https://help.aliyun.com/zh/dashscope/)
- [MOSES项目](../src/external/MOSES/)

## 🆘 获取帮助

- 查看日志输出（带`[Chatbot]`和`[MOSES]`前缀）
- 运行测试脚本诊断问题
- 检查配置文件语法（YAML格式）
- 确认环境变量已设置
