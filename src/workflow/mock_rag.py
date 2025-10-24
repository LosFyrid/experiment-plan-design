"""Mock RAG检索器 - 用于端到端测试

在真实RAG实现之前，使用简单的关键词匹配从mock数据中检索模板
"""

import json
from pathlib import Path
from typing import List, Dict, Any


class MockRAGRetriever:
    """Mock RAG检索器"""

    def __init__(self, templates_file: str = "data/mock/dss_templates.json"):
        """初始化

        Args:
            templates_file: 模板文件路径
        """
        self.templates_file = Path(templates_file)
        self.templates = self._load_templates()

    def _load_templates(self) -> List[Dict]:
        """加载模板数据"""
        if not self.templates_file.exists():
            print(f"[MockRAG] 警告: 模板文件不存在 {self.templates_file}")
            return []

        with open(self.templates_file, 'r', encoding='utf-8') as f:
            templates = json.load(f)

        print(f"[MockRAG] 加载了 {len(templates)} 个模板")
        return templates

    def retrieve(
        self,
        requirements: Dict[str, Any],
        top_k: int = 3
    ) -> List[Dict]:
        """检索相关模板

        使用简单的关键词匹配策略：
        1. 提取requirements中的关键词
        2. 计算每个模板的相关度分数
        3. 返回top_k个最相关的模板

        Args:
            requirements: 需求字典（包含objective, target_compound等）
            top_k: 返回模板数量

        Returns:
            相关模板列表
        """
        if not self.templates:
            return []

        # 提取关键词
        keywords = self._extract_keywords(requirements)
        print(f"[MockRAG] 提取关键词: {keywords}")

        # 计算每个模板的相关度
        scored_templates = []
        for template in self.templates:
            score = self._calculate_relevance(template, keywords)
            scored_templates.append((template, score))

        # 排序并返回top_k
        scored_templates.sort(key=lambda x: x[1], reverse=True)

        top_templates = [t for t, score in scored_templates[:top_k]]

        print(f"[MockRAG] 检索到 {len(top_templates)} 个相关模板:")
        for i, t in enumerate(top_templates, 1):
            print(f"  {i}. {t['title']}")

        return top_templates

    def _extract_keywords(self, requirements: Dict) -> List[str]:
        """从需求中提取关键词"""
        keywords = []

        # 从objective提取
        if "objective" in requirements:
            objective = requirements["objective"].lower()
            keywords.append(objective)

        # 从target_compound提取
        if "target_compound" in requirements:
            target = requirements["target_compound"].lower()
            keywords.append(target)

        # 从constraints提取
        if "constraints" in requirements:
            for constraint in requirements["constraints"]:
                keywords.append(constraint.lower())

        # 从special_requirements提取
        if "special_requirements" in requirements:
            keywords.append(requirements["special_requirements"].lower())

        return keywords

    def _calculate_relevance(
        self,
        template: Dict,
        keywords: List[str]
    ) -> float:
        """计算模板与关键词的相关度

        简单策略：统计关键词在模板各字段中出现的次数
        """
        score = 0.0

        # 在标题中搜索（权重高）
        title = template.get("title", "").lower()
        for keyword in keywords:
            if keyword in title:
                score += 3.0

        # 在摘要中搜索
        summary = template.get("procedure_summary", "").lower()
        for keyword in keywords:
            if keyword in summary:
                score += 2.0

        # 在关键点中搜索
        key_points = template.get("key_points", [])
        for point in key_points:
            point_lower = point.lower()
            for keyword in keywords:
                if keyword in point_lower:
                    score += 1.0

        # 在难度级别中搜索
        if "constraints" in " ".join(keywords):
            difficulty = template.get("difficulty", "")
            # 如果需求提到"基础"/"简单"，优先匹配beginner
            if any(word in " ".join(keywords) for word in ["基础", "简单", "入门"]):
                if difficulty == "beginner":
                    score += 1.5
            # 如果提到"高级"/"复杂"，优先匹配advanced
            elif any(word in " ".join(keywords) for word in ["高级", "复杂", "精密"]):
                if difficulty == "advanced":
                    score += 1.5

        return score


def create_mock_rag_retriever(templates_file: str = "data/mock/dss_templates.json"):
    """创建Mock RAG检索器的工厂函数"""
    return MockRAGRetriever(templates_file)
