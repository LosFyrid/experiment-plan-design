"""化学实验助手Chatbot主类

基于LangGraph的create_react_agent预制组件，提供：
- 自动工具调用（MOSES本体查询）
- 对话记忆管理（内存/SQLite双模式）
- 流式响应支持
"""
import os
from typing import Optional, List, Dict, Any, Iterator
from pathlib import Path

# 加载.env文件（如果存在）
from dotenv import load_dotenv
load_dotenv()

from langchain_community.chat_models.tongyi import ChatTongyi
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

# SQLite checkpointer是可选的
try:
    from langgraph.checkpoint.sqlite import SqliteSaver
    SQLITE_AVAILABLE = True
except ImportError:
    try:
        from langgraph_checkpoint_sqlite import SqliteSaver
        SQLITE_AVAILABLE = True
    except ImportError:
        SqliteSaver = None
        SQLITE_AVAILABLE = False

from .tools import MOSESToolWrapper
from .config import load_config


class Chatbot:
    """化学实验助手Chatbot

    核心特性：
    - 使用qwen-plus模型（支持thinking）
    - 自动调用MOSES本体查询工具
    - 支持内存和SQLite两种记忆模式
    - 支持流式响应（实时打字效果）
    """

    def __init__(self, config_path: str = "configs/chatbot_config.yaml"):
        """初始化Chatbot

        Args:
            config_path: 配置文件路径

        Raises:
            FileNotFoundError: 配置文件不存在
            ValueError: 配置验证失败
        """
        # 加载配置
        self.config = load_config(config_path)

        # 初始化LLM
        self.llm = self._init_llm()

        # 创建MOSES wrapper（不启动后台初始化）
        self.moses_wrapper = MOSESToolWrapper(self.config["chatbot"]["moses"], auto_init=False)

        # 初始化checkpointer
        self.checkpointer = self._init_checkpointer()

        # 使用LangGraph预制agent
        system_prompt = self.config["chatbot"].get(
            "system_prompt",
            "你是一个专业的化学实验助手，可以查询化学本体知识库来回答问题。"
        )

        moses_tool = self.moses_wrapper.get_tool()
        self.agent = create_react_agent(
            model=self.llm,
            tools=[moses_tool],
            checkpointer=self.checkpointer,
            state_modifier=system_prompt
        )

        # 启动MOSES后台初始化（静默）
        self.moses_wrapper.start_init()

    def _init_llm(self):
        """初始化qwen-plus LLM（支持thinking）

        Returns:
            ChatTongyi实例
        """
        llm_config = self.config["chatbot"]["llm"]

        # qwen-plus的thinking功能需要特殊配置
        model_kwargs = {
            "temperature": llm_config.get("temperature", 0.7),
            "max_tokens": llm_config.get("max_tokens", 4096),
        }

        # 如果启用thinking，需要同时启用incremental_output
        if llm_config.get("enable_thinking", False):
            model_kwargs["enable_thinking"] = True
            model_kwargs["incremental_output"] = True  # thinking必需参数

        return ChatTongyi(
            model_name=llm_config["model_name"],
            model_kwargs=model_kwargs
        )

    def _init_checkpointer(self):
        """初始化记忆checkpointer

        根据配置选择：
        - in_memory: MemorySaver（开发调试用，会话结束后丢失）
        - sqlite: SqliteSaver（持久化，可恢复历史会话）

        Returns:
            Checkpointer实例
        """
        memory_config = self.config["chatbot"]["memory"]
        memory_type = memory_config.get("type", "in_memory")

        if memory_type == "sqlite":
            if not SQLITE_AVAILABLE:
                # 静默降级为内存模式
                return MemorySaver()

            sqlite_path = memory_config["sqlite_path"]
            # 确保目录存在
            Path(sqlite_path).parent.mkdir(parents=True, exist_ok=True)
            return SqliteSaver.from_conn_string(sqlite_path)
        else:
            return MemorySaver()

    def chat(self, message: str, session_id: str = "default") -> str:
        """发送消息并获取完整回复（非流式）

        Args:
            message: 用户消息
            session_id: 会话ID（用于区分不同用户/会话）

        Returns:
            助手的完整回复文本
        """
        config = {"configurable": {"thread_id": session_id}}

        response = self.agent.invoke(
            {"messages": [{"role": "user", "content": message}]},
            config=config
        )

        # 提取最后一条助手消息
        return response["messages"][-1].content

    def stream_chat(self, message: str, session_id: str = "default", show_thinking: bool = True) -> Iterator[Dict[str, Any]]:
        """发送消息并流式获取回复（token级流式）

        使用stream_mode="messages"实现逐token流式传输

        Args:
            message: 用户消息
            session_id: 会话ID
            show_thinking: 是否显示thinking过程（qwen-plus特性）

        Yields:
            字典包含 {"type": "thinking"|"content"|"tool_call"|"tool_result", "data": str}
        """
        config = {"configurable": {"thread_id": session_id}}

        # 使用messages模式获取token级别的流式输出
        for event in self.agent.stream(
            {"messages": [{"role": "user", "content": message}]},
            config=config,
            stream_mode="messages"
        ):
            # event是(message, metadata)元组
            if isinstance(event, tuple) and len(event) == 2:
                msg, metadata = event

                # 获取节点名称
                node_name = metadata.get("langgraph_node", "")

                # 处理来自agent节点的消息
                if node_name == "agent":
                    # AIMessageChunk - 流式token
                    if msg.__class__.__name__ == "AIMessageChunk":
                        # 检查thinking（从additional_kwargs获取reasoning_content）
                        if show_thinking and hasattr(msg, "additional_kwargs"):
                            reasoning = msg.additional_kwargs.get("reasoning_content", "")
                            # 只有非空时才yield（自动跳过空thinking）
                            if reasoning:
                                yield {
                                    "type": "thinking",
                                    "data": reasoning
                                }

                        # 流式内容token
                        if hasattr(msg, "content") and msg.content:
                            yield {
                                "type": "content",
                                "data": msg.content
                            }

                    # 工具调用消息（ToolMessage）
                    elif msg.__class__.__name__ == "ToolMessage":
                        if hasattr(msg, "name"):
                            yield {
                                "type": "tool_call",
                                "data": msg.name
                            }

                # 工具节点的响应
                elif node_name == "tools":
                    if hasattr(msg, "content") and msg.content:
                        yield {
                            "type": "tool_result",
                            "data": msg.content
                        }

    def get_history(self, session_id: str = "default") -> List[Dict]:
        """获取会话历史消息

        Args:
            session_id: 会话ID

        Returns:
            消息列表，每条消息包含role和content
        """
        config = {"configurable": {"thread_id": session_id}}

        try:
            state = self.agent.get_state(config)
            messages = state.values.get("messages", [])

            # 转换为简单字典格式
            history = []
            for msg in messages:
                if hasattr(msg, "type"):
                    role = msg.type  # "human" or "ai"
                    # 统一转换为user/assistant
                    if role == "human":
                        role = "user"
                    elif role == "ai":
                        role = "assistant"
                else:
                    role = "unknown"

                history.append({
                    "role": role,
                    "content": msg.content if hasattr(msg, "content") else str(msg)
                })

            return history
        except Exception as e:
            # 静默失败，返回空历史
            return []

    def list_sessions(self) -> List[str]:
        """列出所有会话ID（仅SQLite模式支持）

        Returns:
            会话ID列表

        Note:
            内存模式无法列出会话，返回空列表
        """
        if SQLITE_AVAILABLE and isinstance(self.checkpointer, SqliteSaver):
            # SQLite模式：查询数据库获取所有thread_id
            try:
                # 注意：LangGraph的SqliteSaver没有直接的list接口
                # 这里需要直接查询数据库
                conn = self.checkpointer.conn
                cursor = conn.execute("SELECT DISTINCT thread_id FROM checkpoints")
                return [row[0] for row in cursor.fetchall()]
            except Exception as e:
                return []
        else:
            # 内存模式：无法持久化查询
            return []

    def cleanup(self):
        """清理资源

        停止MOSES QueryManager，释放资源
        """
        self.moses_wrapper.cleanup()
