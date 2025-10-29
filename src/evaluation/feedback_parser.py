"""
人工反馈文件解析器

解析YAML格式的人工反馈文件，转换为Feedback对象。
"""

from pathlib import Path
from typing import Dict, List
import yaml
from datetime import datetime

from ace_framework.playbook.schemas import Feedback, FeedbackScore


class FeedbackParser:
    """解析人工反馈YAML文件"""

    def parse_file(self, file_path: str) -> Feedback:
        """
        解析反馈文件

        Args:
            file_path: YAML文件路径

        Returns:
            Feedback对象

        Raises:
            ValueError: 文件格式错误或验证失败
        """
        # 读取YAML
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        # 验证数据
        errors = self._validate(data)
        if errors:
            raise ValueError(
                "反馈文件验证失败:\n" +
                "\n".join(f"  • {e}" for e in errors)
            )

        # 转换为Feedback对象
        return self._to_feedback(data)

    def _validate(self, data: Dict) -> List[str]:
        """
        验证反馈数据

        Returns:
            错误列表（空列表表示验证通过）
        """
        errors = []

        # 1. criteria字段必须存在
        if "criteria" not in data:
            errors.append("缺少 'criteria' 字段")
            return errors

        criteria = data["criteria"]

        # 2. 至少1个维度
        if not criteria or len(criteria) == 0:
            errors.append("至少需要1个评估维度")

        # 3. 每个维度的字段检查
        for i, c in enumerate(criteria, 1):
            # name必填
            if "name" not in c or not c["name"].strip():
                errors.append(f"第{i}个维度缺少 'name' 字段")

            # score必填且在0-10范围
            if "score" not in c:
                errors.append(f"第{i}个维度 '{c.get('name', '?')}' 缺少 'score' 字段")
            else:
                try:
                    score = float(c["score"])
                    if not 0 <= score <= 10:
                        errors.append(
                            f"第{i}个维度 '{c.get('name')}' 的分数必须在0-10之间 (当前: {score})"
                        )
                except (ValueError, TypeError):
                    errors.append(f"第{i}个维度 '{c.get('name')}' 的分数格式错误")

            # explanation必填且≥10字符
            if "explanation" not in c or not c["explanation"]:
                errors.append(
                    f"第{i}个维度 '{c.get('name')}' 缺少 'explanation' 字段 "
                    "(必填！AI从这里学习)"
                )
            elif len(str(c["explanation"]).strip()) < 10:
                errors.append(
                    f"第{i}个维度 '{c.get('name')}' 的 explanation 太短 "
                    f"(至少10字符，当前{len(str(c['explanation']).strip())}字符)"
                )

        # 4. 检查重复name
        names = [c.get("name", "").strip() for c in criteria]
        if len(names) != len(set(names)):
            duplicates = [n for n in names if names.count(n) > 1]
            errors.append(f"检测到重复的维度名称: {', '.join(set(duplicates))}")

        return errors

    def _to_feedback(self, data: Dict) -> Feedback:
        """将解析的数据转换为Feedback对象"""
        scores = []

        for c in data["criteria"]:
            # 转换score: 0-10 → 0-1
            score_normalized = float(c["score"]) / 10.0

            scores.append(FeedbackScore(
                criterion=c["name"].strip(),
                score=score_normalized,
                explanation=str(c["explanation"]).strip()
            ))

        # 计算平均分
        overall_score = sum(s.score for s in scores) / len(scores)

        # 总体评论（可选）
        comments = data.get("overall_comments", "").strip()
        if not comments:
            comments = f"人工评审完成，共评估{len(scores)}个维度"

        return Feedback(
            scores=scores,
            overall_score=overall_score,
            feedback_source="human",
            comments=comments,
            timestamp=datetime.now()
        )


def parse_feedback_file(file_path: str) -> Feedback:
    """
    便捷函数：解析反馈文件

    Args:
        file_path: YAML文件路径

    Returns:
        Feedback对象

    Example:
        >>> feedback = parse_feedback_file("feedback.yaml")
        >>> print(feedback.overall_score)
        0.85
    """
    parser = FeedbackParser()
    return parser.parse_file(file_path)
