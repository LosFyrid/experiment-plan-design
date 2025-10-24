"""MOSES本体查询工具封装

将MOSES QueryManager封装为LangChain Tool，供LangGraph agent使用。
"""
from typing import Dict, Any, Optional
from concurrent.futures import Future
from pathlib import Path
import threading
import sys
import io
import re
import warnings
import contextlib
from langchain_core.tools import tool


class MOSESToolWrapper:
    """MOSES QueryManager封装器

    将MOSES的本体查询功能封装为LangChain Tool，
    处理QueryManager的生命周期管理和后台初始化。

    特性：
    - 支持延迟启动后台初始化（避免影响主线程）
    - 使用threading.Event确保初始化完成后才执行查询
    - 保存初始化错误供后续查询时抛出
    - 过滤MOSES内部日志，只显示关键统计信息
    """

    def __init__(self, config: Dict[str, Any], auto_init: bool = True):
        """初始化MOSES工具封装器

        Args:
            config: MOSES配置字典，包含max_workers和query_timeout
            auto_init: 是否自动启动后台初始化（默认True，设为False则需手动调用start_init）
        """
        self.config = config
        self.query_manager: Optional[Any] = None
        self._initialized = False

        # 初始化同步机制
        self._init_event = threading.Event()  # 标记初始化完成
        self._init_error: Optional[Exception] = None  # 保存初始化错误

        if auto_init:
            self.start_init()

    def start_init(self):
        """启动后台初始化（可以在主线程初始化完成后调用）"""
        print("[MOSES] 后台初始化已启动...")
        init_thread = threading.Thread(target=self._background_init, daemon=True)
        init_thread.start()

    def _background_init(self):
        """后台线程初始化QueryManager（不捕获输出，让MOSES正常输出）"""
        try:
            import os

            # 添加MOSES根目录到Python路径
            moses_root = Path(__file__).parent.parent / "external" / "MOSES"
            moses_root_str = str(moses_root.resolve())
            if moses_root_str not in sys.path:
                sys.path.insert(0, moses_root_str)

            # 全局屏蔽警告（但不捕获stdout，避免影响主线程）
            warnings.filterwarnings('ignore', category=DeprecationWarning)
            warnings.filterwarnings('ignore', message='.*java_exe.*')

            # 导入和初始化（正常输出到终端）
            from autology_constructor.idea.query_team import QueryManager
            from config.settings import ONTOLOGY_SETTINGS

            self.query_manager = QueryManager(
                max_workers=self.config.get("max_workers", 4),
                ontology_settings=ONTOLOGY_SETTINGS
            )
            self.query_manager.start()
            self._initialized = True

            # 从本体对象中读取统计信息（而不是解析输出）
            self._print_summary_from_ontology(ONTOLOGY_SETTINGS)

        except Exception as e:
            self._init_error = e
            print(f"[MOSES] ✗ 初始化失败: {e}")
        finally:
            self._init_event.set()

    def _print_summary_from_ontology(self, ontology_settings):
        """从已加载的本体对象中读取统计信息（不依赖输出捕获）"""
        try:
            ontology = ontology_settings.ontology

            # 直接从本体对象统计
            classes = list(ontology.classes())
            data_properties = list(ontology.data_properties())
            object_properties = list(ontology.object_properties())

            ontology_path = Path(ontology_settings.directory_path) / ontology_settings.ontology_file_name

            # 打印简洁摘要
            print("\n" + "="*60)
            print("[MOSES] ✓ 本体查询管理器已就绪")
            print(f"[MOSES]   本体文件: {ontology_path}")
            print(f"[MOSES]   统计: {len(classes)} classes, {len(data_properties)} data properties, {len(object_properties)} object properties")
            print("="*60 + "\n")
        except Exception as e:
            print(f"[MOSES] ✓ 本体查询管理器已就绪（统计信息获取失败: {e}）")

    def _print_summary(self, output: str, ontology_settings):
        """从MOSES输出中提取并打印关键统计信息（弃用，保留以防万一）"""
        # 这个方法现在不再使用，但保留代码以防需要回退
        pass

    def _ensure_manager(self):
        """等待初始化完成（如果初始化失败则抛出异常）"""
        if not self._init_event.is_set():
            print("[MOSES] 等待本体初始化完成...")
            self._init_event.wait()  # 阻塞直到初始化完成

        # 检查是否有初始化错误
        if self._init_error is not None:
            raise RuntimeError(f"MOSES初始化失败: {self._init_error}")

        if not self._initialized:
            raise RuntimeError("MOSES初始化未完成（未知原因）")

    def get_tool(self):
        """获取LangChain Tool实例

        Returns:
            装饰后的tool函数，可直接传给create_react_agent
        """
        print("[DEBUG] get_tool() called")
        # 闭包捕获self，避免tool装饰器问题
        wrapper_instance = self

        @tool
        def query_chemistry_knowledge(query: str) -> str:
            """Query the chemistry ontology knowledge base for information about chemical entities, properties, relationships, and experimental procedures.

            Use this tool when you need to:
            - Look up chemical compounds, materials, or substances
            - Find properties of chemical entities
            - Understand relationships between chemicals
            - Get information about experimental techniques or procedures
            - Answer chemistry domain-specific questions

            Args:
                query: Natural language query about chemistry (e.g., "What is quinine?", "Tell me about IDA sensors")

            Returns:
                Formatted knowledge extracted from the chemistry ontology
            """
            wrapper_instance._ensure_manager()

            try:
                print(f"[MOSES] 查询本体: {query}")

                # 提交查询并获取Future
                future: Future = wrapper_instance.query_manager.submit_query(
                    query_text=query,
                    query_context={
                        "originating_team": "chatbot",
                        "originating_agent": "moses_tool"
                    }
                )

                # 同步等待结果（带超时）
                timeout = wrapper_instance.config.get("query_timeout", 30)
                result = future.result(timeout=timeout)

                # 提取格式化结果
                if result.get("formatted_results"):
                    formatted = result["formatted_results"]
                    print(f"[MOSES] 查询成功，返回 {len(formatted)} 字符")
                    return formatted
                else:
                    return "本体知识库中未找到相关信息。"

            except TimeoutError:
                error_msg = f"本体查询超时（{timeout}秒）"
                print(f"[MOSES] {error_msg}")
                return error_msg
            except Exception as e:
                error_msg = f"本体查询出错: {str(e)}"
                print(f"[MOSES] {error_msg}")
                return error_msg

        print("[DEBUG] get_tool() returning tool")
        return query_chemistry_knowledge

    def cleanup(self):
        """清理资源，停止QueryManager（不捕获输出，避免卡死）"""
        if self.query_manager and self._initialized:
            print("[MOSES] 停止查询管理器...")
            try:
                self.query_manager.stop()
                self._initialized = False
                print("[MOSES] 已停止")
            except Exception as e:
                print(f"[MOSES] 停止时出错: {e}")
