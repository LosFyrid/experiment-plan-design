"""
Qwen Embedding Provider - 使用阿里云通义千问的embedding API

支持：
- text-embedding-v4（最新）
- 批量embedding（最多10个文本）
- 缓存优化
"""

import os
from typing import List, Union
import numpy as np


class QwenEmbeddingProvider:
    """
    Qwen Embedding API 提供者。

    使用阿里云通义千问的text-embedding-v4模型。
    """

    def __init__(
        self,
        model: str = "text-embedding-v4",
        api_key: str = None,
        batch_size: int = 10  # Qwen API支持最多10个文本
    ):
        """
        Args:
            model: 模型名称（text-embedding-v4, text-embedding-v3等）
            api_key: API密钥（如果不提供，从环境变量读取）
            batch_size: 批处理大小（Qwen限制最多10）
        """
        self.model = model
        self.batch_size = min(batch_size, 10)  # 确保不超过限制

        # Import dashscope
        try:
            import dashscope
            from dashscope import TextEmbedding
            self.dashscope = dashscope
            self.TextEmbedding = TextEmbedding
        except ImportError:
            raise ImportError(
                "dashscope package not found. Install with: pip install dashscope"
            )

        # Set API key
        if api_key is None:
            api_key = os.getenv("DASHSCOPE_API_KEY")

        if not api_key:
            raise ValueError("DASHSCOPE_API_KEY not provided and not found in environment")

        self.dashscope.api_key = api_key

    def encode(
        self,
        texts: Union[str, List[str]],
        show_progress_bar: bool = False
    ) -> np.ndarray:
        """
        将文本编码为embeddings。

        Args:
            texts: 单个文本字符串或文本列表
            show_progress_bar: 是否显示进度条（保持与sentence-transformers接口一致）

        Returns:
            numpy数组：(n_texts, embedding_dim)
        """
        # 统一处理为列表
        if isinstance(texts, str):
            texts = [texts]

        # 如果为空，返回空数组
        if not texts:
            return np.array([])

        # 批量处理
        all_embeddings = []

        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            batch_embeddings = self._encode_batch(batch)
            all_embeddings.extend(batch_embeddings)

        return np.array(all_embeddings)

    def _encode_batch(self, texts: List[str]) -> List[List[float]]:
        """
        批量编码一批文本。

        Args:
            texts: 文本列表（最多10个）

        Returns:
            embeddings列表
        """
        try:
            # 调用Qwen API
            response = self.TextEmbedding.call(
                model=self.model,
                input=texts
            )

            # 检查错误
            if response.status_code != 200:
                raise RuntimeError(
                    f"Qwen Embedding API error: {response.code} - {response.message}"
                )

            # 提取embeddings
            embeddings = []
            for item in response.output["embeddings"]:
                embeddings.append(item["embedding"])

            return embeddings

        except Exception as e:
            raise RuntimeError(f"Failed to get embeddings from Qwen API: {e}")

    def get_embedding_dim(self) -> int:
        """
        获取embedding维度。

        Returns:
            embedding维度（text-embedding-v4是1024维）
        """
        # text-embedding-v4的维度
        if self.model == "text-embedding-v4":
            return 1024
        elif self.model == "text-embedding-v3":
            return 1024
        elif self.model == "text-embedding-v2":
            return 1536
        elif self.model == "text-embedding-v1":
            return 1536
        else:
            # 默认返回v4的维度，如果不确定可以调用一次API获取
            return 1024


def compute_cosine_similarity(
    embeddings1: np.ndarray,
    embeddings2: np.ndarray
) -> np.ndarray:
    """
    计算余弦相似度。

    Args:
        embeddings1: 形状为(n, dim)的embedding矩阵
        embeddings2: 形状为(m, dim)的embedding矩阵

    Returns:
        相似度矩阵，形状为(n, m)
    """
    # 归一化
    embeddings1_norm = embeddings1 / np.linalg.norm(embeddings1, axis=1, keepdims=True)
    embeddings2_norm = embeddings2 / np.linalg.norm(embeddings2, axis=1, keepdims=True)

    # 计算余弦相似度
    similarity = np.dot(embeddings1_norm, embeddings2_norm.T)

    return similarity


# 为了兼容现有代码中的util.cos_sim调用
class UtilModule:
    """模拟sentence_transformers.util模块的cos_sim函数"""

    @staticmethod
    def cos_sim(a: np.ndarray, b: np.ndarray) -> np.ndarray:
        """
        计算余弦相似度（兼容sentence_transformers.util.cos_sim接口）。

        Args:
            a: 形状为(n, dim)或(dim,)的embedding
            b: 形状为(m, dim)的embedding矩阵

        Returns:
            相似度矩阵
        """
        # 确保是2D
        if a.ndim == 1:
            a = a.reshape(1, -1)
        if b.ndim == 1:
            b = b.reshape(1, -1)

        return compute_cosine_similarity(a, b)


# 导出util以兼容现有代码
util = UtilModule()
