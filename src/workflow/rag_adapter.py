"""RAG 检索适配器

功能：
1. 封装 LargeRAG 调用逻辑
2. 格式转换：LargeRAG 输出 → Generator 需要的格式
3. 统一错误处理
4. 惰性初始化（只在第一次调用时加载RAG）

设计原则：
- 只传递必要字段给 Generator（title, content, score）
- 避免传递冗余的 metadata 字段
- 确保与 Generator prompts 兼容
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
import sys
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RAGAdapter:
    """RAG 检索适配器 - 统一 RAG 接口"""

    def __init__(self, config_path: Optional[str] = None):
        """初始化（惰性加载）

        Args:
            config_path: RAG 配置文件路径（可选）
        """
        self.config_path = config_path
        self._rag = None  # 延迟初始化
        self._initialized = False

    def _ensure_initialized(self):
        """确保 RAG 已初始化"""
        if self._initialized:
            return

        logger.info("[RAGAdapter] 正在初始化 LargeRAG...")

        try:
            # 动态导入（避免启动时加载）
            # 添加项目根目录到路径
            current_file = Path(__file__).resolve()
            project_root = current_file.parent.parent.parent
            src_path = project_root / "src"

            if str(src_path) not in sys.path:
                sys.path.insert(0, str(src_path))

            # 导入 LargeRAG（使用绝对导入）
            from external.rag.largerag import LargeRAG

            # 初始化
            self._rag = LargeRAG(config_path=self.config_path)

            # 检查索引是否存在
            if self._rag.query_engine is None:
                logger.warning(
                    "[RAGAdapter] ⚠️  索引未加载！需要先运行 index_from_folders()"
                )
                logger.warning(
                    "[RAGAdapter] 将在首次检索时尝试自动加载索引"
                )

            self._initialized = True
            logger.info("[RAGAdapter] ✅ LargeRAG 初始化完成")

        except Exception as e:
            logger.error(f"[RAGAdapter] ❌ 初始化失败: {e}")
            raise RuntimeError(f"RAG 初始化失败: {e}")

    def retrieve_templates(
        self,
        requirements: Dict[str, Any],
        top_k: int = 5
    ) -> List[Dict]:
        """检索相关模板/文档

        Args:
            requirements: 结构化需求（从 MOSES 提取）
            top_k: 返回文档数量（默认 5）

        Returns:
            精简的模板列表，每个模板包含:
            - title: str (生成的标题)
            - content: str (完整文本内容)
            - score: float (相关度分数)

        Notes:
            - 返回格式针对 Generator 的 prompts 优化
            - 不包含冗余的 metadata 字段
            - 如果检索失败，返回空列表（不抛异常）
        """
        # 确保初始化
        try:
            self._ensure_initialized()
        except Exception as e:
            logger.error(f"[RAGAdapter] 初始化失败，返回空列表: {e}")
            return []

        # 1. 构建查询字符串
        query = self._build_query(requirements)
        logger.info(f"[RAGAdapter] 查询: {query}")

        # 2. 调用 LargeRAG
        try:
            docs = self._rag.get_similar_docs(
                query_text=query,
                top_k=top_k
            )
            logger.info(f"[RAGAdapter] ✅ 检索到 {len(docs)} 个相关文档")

        except Exception as e:
            logger.error(f"[RAGAdapter] ❌ 检索失败: {e}")
            import traceback
            traceback.print_exc()
            return []

        # 3. 格式转换（精简版）
        templates = self._convert_to_template_format(docs)

        # 4. 打印预览
        self._print_preview(templates)

        return templates

    def _build_query(self, requirements: Dict[str, Any]) -> str:
        """从 requirements 构建查询字符串

        Args:
            requirements: 需求字典

        Returns:
            查询字符串
        """
        parts = []

        # 优先级：objective > target_compound > constraints
        if "objective" in requirements:
            parts.append(requirements["objective"])

        if "target_compound" in requirements:
            parts.append(requirements["target_compound"])

        if "constraints" in requirements and requirements["constraints"]:
            # 只取前3个约束（避免过长）
            constraints = requirements["constraints"][:3]
            parts.append(" ".join(constraints))

        query = " ".join(parts)

        # 如果查询为空，使用默认查询
        if not query.strip():
            query = "实验方案"
            logger.warning(f"[RAGAdapter] ⚠️  需求为空，使用默认查询: {query}")

        return query

    def _convert_to_template_format(self, docs: List[Dict]) -> List[Dict]:
        """
        将 LargeRAG 输出转换为 Generator 需要的精简格式

        LargeRAG 输出格式:
        {
            "text": "文档内容...",
            "score": 0.85,
            "metadata": {
                "doc_hash": "xxx",
                "page_idx": 0,
                ...很多字段...
            }
        }

        Generator 需要格式（精简）:
        {
            "title": "相关文献 1 (相关度: 0.85)",
            "content": "文档内容...",
            "score": 0.85
        }

        设计原则：
        - 只保留必要字段（title, content, score）
        - 不传递冗余的 metadata
        - title 生成简洁描述性标题
        """
        templates = []

        for i, doc in enumerate(docs, 1):
            # 提取文本内容
            text = doc.get("text", "")
            score = doc.get("score", 0.0)

            # 生成简洁标题（包含相关度信息）
            title = f"相关文献 {i} (相关度: {score:.3f})"

            # 可选：从 content 前50字符生成更描述性的标题
            if len(text) > 50:
                preview = text[:50].replace("\n", " ").strip() + "..."
                title = f"文献 {i}: {preview}"

            # 构建精简模板
            template = {
                "title": title,
                "content": text,  # 完整内容，让 Generator 自己处理
                "score": score,   # 保留分数供参考
                # 不包含 metadata（避免冗余）
            }

            templates.append(template)

        return templates

    def _print_preview(self, templates: List[Dict]):
        """打印检索结果预览"""
        if not templates:
            logger.info("[RAGAdapter] 无检索结果")
            return

        logger.info(f"[RAGAdapter] 检索结果预览（共 {len(templates)} 个）:")
        for i, t in enumerate(templates[:3], 1):  # 只打印前3个
            score = t.get("score", 0)
            content_preview = t["content"][:80].replace("\n", " ")
            logger.info(f"  {i}. [{score:.3f}] {content_preview}...")


# ============================================================================
# 工厂函数
# ============================================================================

def create_rag_adapter(config_path: Optional[str] = None) -> RAGAdapter:
    """创建 RAG 适配器的工厂函数

    Args:
        config_path: RAG 配置文件路径（可选）

    Returns:
        RAGAdapter 实例
    """
    return RAGAdapter(config_path=config_path)
