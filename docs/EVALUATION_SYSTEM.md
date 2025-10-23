# 反馈系统详解

## 问题：Reflector的反馈从哪里来？

在ACE框架中，Reflector需要**反馈（Feedback）**来分析生成的实验方案。这个反馈告诉Reflector：
- 方案的质量如何？
- 哪些地方做得好？
- 哪些地方需要改进？

## 完整的ACE流程

```
需求 → [Generator] → 实验方案 → [评估系统] → Feedback → [Reflector] → Insights → [Curator] → 更新Playbook
```

**关键步骤**：
1. Generator生成方案
2. **评估系统**对方案打分 ← 这一步产生Feedback！
3. Reflector使用Feedback进行反思
4. Curator根据insights更新playbook

## 三种评估方式

我们实现了三种评估方式，在`src/evaluation/evaluator.py`中：

### 1. Auto评估（自动规则检查）

**特点**：
- ✅ 快速（<1秒）
- ✅ 免费（不消耗API tokens）
- ✅ 可靠（基于明确规则）
- ❌ 只能检查格式，不能判断内容质量

**工作原理**：
```python
from evaluation.evaluator import evaluate_plan

feedback = evaluate_plan(
    plan=generated_plan,
    source="auto"  # 使用自动评估
)
```

**检查项目**：
- **完整性**：是否包含所有必需字段（标题、材料、步骤、安全提示等）
- **安全性**：是否有安全提示
- **清晰度**：步骤是否有编号和描述
- **可执行性**：步骤数量是否合理（3-20步）
- **成本效益**：默认中等分（auto模式无法准确判断）

**示例输出**：
```json
{
  "overall_score": 0.87,
  "feedback_source": "auto",
  "scores": [
    {"criterion": "completeness", "score": 1.0, "explanation": "包含所有必需部分"},
    {"criterion": "safety", "score": 0.9, "explanation": "包含3条安全提示"},
    {"criterion": "clarity", "score": 0.8, "explanation": "包含8个步骤，描述较为清晰"},
    {"criterion": "executability", "score": 0.8, "explanation": "步骤数量合理(8步)，包含必要的操作参数"},
    {"criterion": "cost_effectiveness", "score": 0.7, "explanation": "自动评估无法准确判断成本效益"}
  ],
  "comments": "方案质量良好，可进一步完善"
}
```

### 2. LLM Judge评估（使用LLM打分）

**特点**：
- ✅ 准确（接近人类判断）
- ✅ 可以评估内容质量
- ✅ 提供详细解释
- ❌ 消耗额外tokens（每次评估约500-1000 tokens）
- ❌ 较慢（2-5秒）

**工作原理**：
```python
feedback = evaluate_plan(
    plan=generated_plan,
    source="llm_judge",
    llm_provider=llm_provider  # 需要提供LLM
)
```

**评估过程**：
1. 将生成的方案转为文本
2. 构建评估prompt（包含评分标准）
3. 调用LLM进行评分
4. 解析LLM返回的JSON格式评分

**LLM评估prompt示例**：
```
请评估以下实验方案：

实验方案：
标题：合成阿司匹林
目标：从水杨酸合成乙酰水杨酸

材料清单：
- 水杨酸: 2.0g (纯度: ≥99%)
- 乙酸酐: 5.0mL
...

评估标准：completeness, safety, clarity, executability, cost_effectiveness

请为每个标准打分（0-1之间的浮点数），并给出总体评分和评论。

返回JSON格式：
{
  "scores": [
    {"criterion": "completeness", "score": 0.9, "explanation": "..."},
    ...
  ],
  "overall_score": 0.88,
  "comments": "总体评价..."
}
```

**成本估算**：
- 输入：约500 tokens（方案内容）
- 输出：约300 tokens（评分结果）
- 总计：约800 tokens/次评估
- qwen-max成本：800 × 0.12 / 1000 = 0.096元/次

### 3. Human评估（人工打分）

**特点**：
- ✅ 最准确（专家判断）
- ❌ 慢（需要人工介入）
- ❌ 贵（人力成本）
- ❌ 无法规模化

**当前实现**：
占位符实现，返回模拟评分。在实际系统中，需要：
1. 将方案保存到待评分队列
2. 通知评分专家
3. 等待专家完成评分
4. 从数据库获取评分结果

**未来可能的实现**：
- Web评分界面
- 评分任务队列系统
- 评分结果数据库

## 如何使用

### 方式1：在.env中配置（推荐）

```bash
# 添加到.env文件
EVALUATION_MODE=auto  # 或 "llm_judge" 或 "human"
```

然后运行：
```bash
python examples/run_simple_ace.py
```

脚本会自动读取配置并使用对应的评估方式。

### 方式2：直接在代码中指定

```python
from evaluation.evaluator import evaluate_plan

# 使用auto评估（快速、免费）
feedback = evaluate_plan(
    plan=generated_plan,
    source="auto"
)

# 或使用LLM评估（准确、消耗tokens）
feedback = evaluate_plan(
    plan=generated_plan,
    source="llm_judge",
    llm_provider=llm_provider
)
```

### 方式3：使用评估器类

```python
from evaluation.evaluator import AutoEvaluator, LLMJudgeEvaluator

# 创建评估器
auto_evaluator = AutoEvaluator()
feedback = auto_evaluator.evaluate(generated_plan)

# 或使用LLM评估器
llm_evaluator = LLMJudgeEvaluator(llm_provider)
feedback = llm_evaluator.evaluate(
    plan=generated_plan,
    criteria=["completeness", "safety", "clarity"]
)
```

## 选择评估方式的建议

### 开发调试阶段
→ 使用 **auto** 模式
- 快速迭代
- 不消耗API额度
- 足以发现明显问题

### 质量评估阶段
→ 使用 **llm_judge** 模式
- 更准确的质量评分
- 可以评估内容合理性
- 适合评估playbook进化效果

### 生产部署阶段
→ 混合模式
- 先用auto快速筛选
- 对得分低的方案使用llm_judge复评
- 关键方案可选择human评审

**示例：混合评估策略**
```python
# 先用auto评估
auto_feedback = evaluate_plan(plan, source="auto")

if auto_feedback.overall_score < 0.7:
    # 得分低，用LLM复评
    feedback = evaluate_plan(plan, source="llm_judge", llm_provider=llm)
else:
    # 得分可接受，直接使用auto结果
    feedback = auto_feedback
```

## 评估标准说明

所有评估方式都使用以下5个标准（在`configs/ace_config.yaml`中配置）：

1. **completeness（完整性）**
   - 是否包含所有必需部分：标题、目标、材料、步骤、安全提示、预期结果、质量控制
   - 满分：包含全部7个必需部分

2. **safety（安全性）**
   - 是否有充分的安全提示
   - 步骤中是否标注危险操作的注意事项
   - 满分：总体安全提示 + 步骤级安全提示

3. **clarity（清晰度）**
   - 步骤是否有明确编号
   - 描述是否清晰易懂
   - 材料用量是否明确
   - 满分：编号清晰 + 描述完整 + 用量明确

4. **executability（可执行性）**
   - 步骤数量是否合理（3-20步）
   - 是否包含时间、温度等关键参数
   - 满分：步骤合理 + 参数完整

5. **cost_effectiveness（成本效益）**
   - 材料成本是否合理
   - 时间成本是否合理
   - **注意**：auto模式无法准确评估，默认给0.7分

## 扩展评估系统

### 添加新的评估标准

编辑`configs/ace_config.yaml`：
```yaml
evaluation:
  evaluation_criteria:
    - completeness
    - safety
    - clarity
    - executability
    - cost_effectiveness
    - reproducibility  # 新增：可重复性
    - environmental_impact  # 新增：环境影响
```

然后在`AutoEvaluator`中实现对应的检查方法：
```python
def _check_reproducibility(self, plan: ExperimentPlan) -> float:
    """检查可重复性"""
    # 实现你的检查逻辑
    pass
```

### 自定义评估器

```python
from evaluation.evaluator import BaseLLMProvider
from ace_framework.playbook.schemas import Feedback, FeedbackScore

class CustomEvaluator:
    """自定义评估器"""

    def evaluate(self, plan, criteria):
        # 实现你的评估逻辑
        scores = [...]

        return Feedback(
            scores=scores,
            overall_score=...,
            feedback_source="custom",
            comments="..."
        )
```

## 常见问题

### Q1: 为什么需要评估系统？

A: ACE框架的核心是**自我改进**：
```
方案生成 → 评估 → 反思 → 改进playbook → 下次生成更好
```

没有评估，Reflector就不知道方案质量如何，无法提取有效的insights来改进playbook。

### Q2: auto评估够用吗？

A: 取决于场景：
- **开发调试**：够用，快速发现格式问题
- **playbook训练**：不够，需要llm_judge评估内容质量
- **生产使用**：建议混合使用（auto筛选 + llm_judge复评）

### Q3: LLM评估会消耗多少tokens？

A: 每次评估约800-1200 tokens：
- 输入：方案内容 + 评估标准（500-700 tokens）
- 输出：评分结果（300-500 tokens）
- 成本：约0.10-0.15元/次（qwen-max）

### Q4: 能否使用更便宜的模型做评估？

A: 可以！
```python
from utils.llm_provider import QwenProvider

# 使用qwen-plus评估（更便宜）
eval_llm = QwenProvider(model_name="qwen-plus")

feedback = evaluate_plan(
    plan=generated_plan,
    source="llm_judge",
    llm_provider=eval_llm  # 使用qwen-plus
)
```

**注意**：ACE论文建议Generator和Reflector使用同样的模型，但Evaluator可以使用不同模型。

### Q5: 如何实现人工评分？

A: 需要构建：
1. **评分界面**：Web UI显示方案，收集评分
2. **任务队列**：管理待评分方案
3. **数据库**：存储评分结果
4. **API接口**：供HumanEvaluator查询评分

示例架构：
```
方案 → 保存到DB → 通知评分员 → 评分员打分 → 保存结果 → HumanEvaluator获取
```

## 总结

**反馈的来源**：评估系统（evaluation）

**三种方式**：
1. **auto**：快速、免费、检查格式
2. **llm_judge**：准确、消耗tokens、评估质量
3. **human**：最准确、慢、贵

**推荐用法**：
- 开发时用auto
- 训练playbook时用llm_judge
- 生产环境用混合策略

**现在你可以运行**：
```bash
# 使用auto评估（默认）
python examples/run_simple_ace.py

# 或使用LLM评估
EVALUATION_MODE=llm_judge python examples/run_simple_ace.py
```
