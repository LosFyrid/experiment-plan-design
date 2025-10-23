"""
评估系统 - 为ACE Reflector提供反馈

实现三种评估方式：
- auto: 基于规则的自动检查（快速、免费）
- llm_judge: 使用LLM评估方案质量（准确、消耗tokens）
- human: 人工评分（最准确、需要人工介入）
"""

from .evaluator import (
    AutoEvaluator,
    LLMJudgeEvaluator,
    HumanEvaluator,
    create_evaluator,
    evaluate_plan
)

__all__ = [
    "AutoEvaluator",
    "LLMJudgeEvaluator",
    "HumanEvaluator",
    "create_evaluator",
    "evaluate_plan"
]
