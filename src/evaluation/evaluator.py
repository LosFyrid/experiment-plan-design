"""
评估系统 - 为Reflector提供反馈

实现三种评估方式：
1. auto: 基于规则的自动检查
2. llm_judge: 使用LLM评估方案质量
3. human: 人工评分（占位符）

根据配置：configs/ace_config.yaml -> evaluation
"""

from typing import List, Optional, Dict, Any
from datetime import datetime

from ace_framework.playbook.schemas import (
    ExperimentPlan,
    Feedback,
    FeedbackScore
)
from utils.llm_provider import BaseLLMProvider


class AutoEvaluator:
    """
    基于规则的自动评估器。

    快速检查方案的完整性和基本质量。
    """

    def evaluate(self, plan: ExperimentPlan) -> Feedback:
        """
        自动评估实验方案。

        Args:
            plan: 生成的实验方案

        Returns:
            Feedback对象
        """
        scores = []

        # 1. 完整性检查
        completeness_score = self._check_completeness(plan)
        scores.append(FeedbackScore(
            criterion="completeness",
            score=completeness_score,
            explanation=self._get_completeness_explanation(plan)
        ))

        # 2. 安全性检查
        safety_score = self._check_safety(plan)
        scores.append(FeedbackScore(
            criterion="safety",
            score=safety_score,
            explanation=self._get_safety_explanation(plan)
        ))

        # 3. 清晰度检查
        clarity_score = self._check_clarity(plan)
        scores.append(FeedbackScore(
            criterion="clarity",
            score=clarity_score,
            explanation=self._get_clarity_explanation(plan)
        ))

        # 4. 可执行性检查
        executability_score = self._check_executability(plan)
        scores.append(FeedbackScore(
            criterion="executability",
            score=executability_score,
            explanation=self._get_executability_explanation(plan)
        ))

        # 5. 成本效益（默认中等）
        scores.append(FeedbackScore(
            criterion="cost_effectiveness",
            score=0.7,
            explanation="自动评估无法准确判断成本效益"
        ))

        # 计算总分
        overall_score = sum(s.score for s in scores) / len(scores)

        return Feedback(
            plan_id=getattr(plan, 'id', None),
            scores=scores,
            overall_score=overall_score,
            feedback_source="auto",
            comments=self._generate_comments(scores, overall_score),
            timestamp=datetime.now()
        )

    def _check_completeness(self, plan: ExperimentPlan) -> float:
        """检查方案完整性"""
        score = 0.0
        checks = 0

        # 必需字段检查
        if plan.title:
            score += 1
        checks += 1

        if plan.objective:
            score += 1
        checks += 1

        if plan.materials and len(plan.materials) > 0:
            score += 1
        checks += 1

        if plan.procedure and len(plan.procedure) > 0:
            score += 1
        checks += 1

        if plan.safety_notes and len(plan.safety_notes) > 0:
            score += 1
        checks += 1

        if plan.expected_outcome:
            score += 1
        checks += 1

        if plan.quality_control and len(plan.quality_control) > 0:
            score += 1
        checks += 1

        return score / checks

    def _check_safety(self, plan: ExperimentPlan) -> float:
        """检查安全性"""
        score = 0.7  # 基准分

        # 有安全提示 +0.2
        if plan.safety_notes and len(plan.safety_notes) > 0:
            score += 0.2

        # 步骤中包含安全提示 +0.1
        for step in plan.procedure:
            if step.safety_notes and len(step.safety_notes) > 0:
                score += 0.1
                break

        return min(score, 1.0)

    def _check_clarity(self, plan: ExperimentPlan) -> float:
        """检查清晰度"""
        score = 0.5  # 基准分

        # 步骤有编号 +0.2
        if all(step.step_number > 0 for step in plan.procedure):
            score += 0.2

        # 步骤有描述 +0.2
        if all(step.description for step in plan.procedure):
            score += 0.2

        # 材料有明确用量 +0.1
        if all(m.amount for m in plan.materials):
            score += 0.1

        return min(score, 1.0)

    def _check_executability(self, plan: ExperimentPlan) -> float:
        """检查可执行性"""
        score = 0.6  # 基准分

        # 步骤数量合理（3-20步） +0.2
        if 3 <= len(plan.procedure) <= 20:
            score += 0.2

        # 有时间估计 +0.1
        if any(step.duration for step in plan.procedure):
            score += 0.1

        # 有温度条件 +0.1
        if any(step.temperature for step in plan.procedure):
            score += 0.1

        return min(score, 1.0)

    def _get_completeness_explanation(self, plan: ExperimentPlan) -> str:
        """生成完整性评分解释"""
        missing = []
        if not plan.title:
            missing.append("标题")
        if not plan.materials or len(plan.materials) == 0:
            missing.append("材料清单")
        if not plan.safety_notes or len(plan.safety_notes) == 0:
            missing.append("安全提示")

        if missing:
            return f"缺少: {', '.join(missing)}"
        return "包含所有必需部分"

    def _get_safety_explanation(self, plan: ExperimentPlan) -> str:
        """生成安全性评分解释"""
        if not plan.safety_notes:
            return "缺少总体安全提示"
        return f"包含{len(plan.safety_notes)}条安全提示"

    def _get_clarity_explanation(self, plan: ExperimentPlan) -> str:
        """生成清晰度评分解释"""
        return f"包含{len(plan.procedure)}个步骤，描述较为清晰"

    def _get_executability_explanation(self, plan: ExperimentPlan) -> str:
        """生成可执行性评分解释"""
        return f"步骤数量合理({len(plan.procedure)}步)，包含必要的操作参数"

    def _generate_comments(self, scores: List[FeedbackScore], overall: float) -> str:
        """生成总体评论"""
        if overall >= 0.9:
            return "方案质量优秀，各方面都符合要求"
        elif overall >= 0.8:
            return "方案质量良好，可进一步完善"
        elif overall >= 0.7:
            return "方案基本符合要求，存在一些可改进之处"
        else:
            # 找出最低分项
            lowest = min(scores, key=lambda s: s.score)
            return f"方案需要改进，特别是{lowest.criterion}方面（{lowest.score:.2f}分）"


class LLMJudgeEvaluator:
    """
    使用LLM评估方案质量。

    通过另一个LLM调用来评估生成的方案。
    """

    def __init__(self, llm_provider: BaseLLMProvider):
        """
        Args:
            llm_provider: LLM提供者（建议使用与Generator相同的模型）
        """
        self.llm = llm_provider

    def evaluate(self, plan: ExperimentPlan, criteria: List[str]) -> Feedback:
        """
        使用LLM评估实验方案。

        Args:
            plan: 生成的实验方案
            criteria: 评估标准列表

        Returns:
            Feedback对象
        """
        # 构建评估prompt
        prompt = self._build_evaluation_prompt(plan, criteria)

        # 调用LLM
        response = self.llm.generate(
            prompt=prompt,
            system_prompt=self._get_system_prompt()
        )

        # 解析响应
        evaluation = self._parse_response(response.content, criteria)

        return evaluation

    def _get_system_prompt(self) -> str:
        """获取系统prompt"""
        return """你是一位资深的化学实验专家和教育者，负责评估实验方案的质量。

你的任务是从以下几个维度对实验方案进行客观、专业的评分：
- completeness（完整性）：是否包含所有必需部分
- safety（安全性）：安全提示是否充分
- clarity（清晰度）：描述是否清晰易懂
- executability（可执行性）：是否可以实际执行
- cost_effectiveness（成本效益）：材料和时间成本是否合理

请以JSON格式返回评分结果。"""

    def _build_evaluation_prompt(self, plan: ExperimentPlan, criteria: List[str]) -> str:
        """构建评估prompt"""
        # 将plan转为可读文本
        plan_text = f"""
实验方案：
标题：{plan.title}
目标：{plan.objective}

材料清单：
{self._format_materials(plan.materials)}

实验步骤：
{self._format_procedure(plan.procedure)}

安全提示：
{self._format_safety_notes(plan.safety_notes)}

预期结果：{plan.expected_outcome}

质量控制：
{self._format_quality_control(plan.quality_control)}
"""

        prompt = f"""请评估以下实验方案：

{plan_text}

评估标准：{', '.join(criteria)}

请为每个标准打分（0-1之间的浮点数），并给出总体评分和评论。

返回JSON格式：
{{
  "scores": [
    {{"criterion": "completeness", "score": 0.9, "explanation": "..."}},
    {{"criterion": "safety", "score": 0.95, "explanation": "..."}},
    ...
  ],
  "overall_score": 0.88,
  "comments": "总体评价..."
}}
"""
        return prompt

    def _format_materials(self, materials) -> str:
        """格式化材料清单"""
        if not materials:
            return "（无）"
        return "\n".join([
            f"- {m.name}: {m.amount or '未指定用量'}" +
            (f" (纯度: {m.purity})" if m.purity else "")
            for m in materials
        ])

    def _format_procedure(self, procedure) -> str:
        """格式化实验步骤"""
        if not procedure:
            return "（无）"
        return "\n".join([
            f"{step.step_number}. {step.description}" +
            (f" (时长: {step.duration})" if step.duration else "") +
            (f" (温度: {step.temperature})" if step.temperature else "")
            for step in procedure
        ])

    def _format_safety_notes(self, safety_notes) -> str:
        """格式化安全提示"""
        if not safety_notes:
            return "（无）"
        return "\n".join([f"- {note}" for note in safety_notes])

    def _format_quality_control(self, qc_checks) -> str:
        """格式化质量控制"""
        if not qc_checks:
            return "（无）"
        return "\n".join([
            f"- {check.check_point}: {check.acceptance_criteria}"
            for check in qc_checks
        ])

    def _parse_response(self, content: str, criteria: List[str]) -> Feedback:
        """解析LLM响应"""
        import json

        # 尝试解析JSON
        try:
            # 移除markdown代码块标记
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            data = json.loads(content.strip())

            # 创建FeedbackScore对象
            scores = [
                FeedbackScore(
                    criterion=s["criterion"],
                    score=float(s["score"]),
                    explanation=s.get("explanation", "")
                )
                for s in data.get("scores", [])
            ]

            return Feedback(
                scores=scores,
                overall_score=float(data.get("overall_score", 0.7)),
                feedback_source="llm_judge",
                comments=data.get("comments", ""),
                timestamp=datetime.now()
            )

        except Exception as e:
            # 解析失败，返回默认评分
            print(f"警告: LLM评估响应解析失败: {e}")
            return self._create_default_feedback(criteria)

    def _create_default_feedback(self, criteria: List[str]) -> Feedback:
        """创建默认反馈（解析失败时使用）"""
        scores = [
            FeedbackScore(
                criterion=c,
                score=0.7,
                explanation="LLM评估响应解析失败，使用默认分数"
            )
            for c in criteria
        ]

        return Feedback(
            scores=scores,
            overall_score=0.7,
            feedback_source="llm_judge",
            comments="LLM评估失败，使用默认评分",
            timestamp=datetime.now()
        )


class HumanEvaluator:
    """
    人工评分（文件模式）

    使用方式:
        1. 复制模板: cp docs/examples/feedback_template.yaml my_feedback.yaml
        2. 编辑文件: 填写criteria和explanation
        3. 调用evaluate()传入文件路径
    """

    def __init__(self, feedback_file: str):
        """
        Args:
            feedback_file: 反馈文件路径（YAML格式）
        """
        self.feedback_file = feedback_file

    def evaluate(self, plan: ExperimentPlan, criteria: List[str] = None) -> Feedback:
        """
        从文件读取人工反馈

        Args:
            plan: 生成的实验方案（用于验证，未使用）
            criteria: 评估标准（兼容性参数，实际从文件读取）

        Returns:
            Feedback对象

        Raises:
            ValueError: 文件不存在或格式错误
        """
        from evaluation.feedback_parser import parse_feedback_file

        # 检查文件存在
        if not Path(self.feedback_file).exists():
            raise ValueError(
                f"反馈文件不存在: {self.feedback_file}\n"
                "请先创建反馈文件:\n"
                "  cp docs/examples/feedback_template.yaml feedback.yaml\n"
                "  vim feedback.yaml"
            )

        # 解析文件
        try:
            feedback = parse_feedback_file(self.feedback_file)
            print(f"✅ 成功解析反馈文件: {len(feedback.scores)}个评估维度")
            return feedback
        except Exception as e:
            raise ValueError(f"解析反馈文件失败: {e}")


# ============================================================================
# 工厂函数
# ============================================================================

def create_evaluator(
    source: str,
    llm_provider: Optional[BaseLLMProvider] = None,
    feedback_file: Optional[str] = None
):
    """
    创建评估器。

    Args:
        source: 评估来源 ("auto", "llm_judge", "human")
        llm_provider: LLM提供者（llm_judge模式需要）
        feedback_file: 反馈文件路径（human模式需要）

    Returns:
        对应的评估器实例

    Raises:
        ValueError: 如果source不支持或缺少必要参数
    """
    if source == "auto":
        return AutoEvaluator()

    elif source == "llm_judge":
        if not llm_provider:
            raise ValueError("llm_judge模式需要提供llm_provider")
        return LLMJudgeEvaluator(llm_provider)

    elif source == "human":
        if not feedback_file:
            raise ValueError(
                "human模式需要提供feedback_file参数\n"
                "用法: create_evaluator('human', feedback_file='feedback.yaml')"
            )
        return HumanEvaluator(feedback_file)

    else:
        raise ValueError(f"不支持的评估来源: {source}，请使用 'auto', 'llm_judge', 或 'human'")


def evaluate_plan(
    plan: ExperimentPlan,
    source: str = "auto",
    criteria: Optional[List[str]] = None,
    llm_provider: Optional[BaseLLMProvider] = None
) -> Feedback:
    """
    便捷函数：评估实验方案。

    Args:
        plan: 实验方案
        source: 评估来源
        criteria: 评估标准列表
        llm_provider: LLM提供者（llm_judge需要）

    Returns:
        Feedback对象
    """
    if criteria is None:
        criteria = [
            "completeness",
            "safety",
            "clarity",
            "executability",
            "cost_effectiveness"
        ]

    evaluator = create_evaluator(source, llm_provider)
    return evaluator.evaluate(plan, criteria) if source != "auto" else evaluator.evaluate(plan)
