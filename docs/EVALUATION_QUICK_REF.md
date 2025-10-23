# 反馈系统快速参考

## 核心概念

**问题**：Reflector的反馈从哪里来？
**答案**：评估系统（Evaluation System）

## ACE完整流程

```
┌─────────────┐
│  用户需求    │
└──────┬──────┘
       ↓
┌─────────────┐
│  Generator  │ ← 使用Playbook生成方案
└──────┬──────┘
       ↓
┌─────────────┐
│  实验方案    │
└──────┬──────┘
       ↓
┌─────────────┐
│ 评估系统 ⭐  │ ← 对方案打分（这里产生Feedback！）
└──────┬──────┘
       ↓
┌─────────────┐
│  Feedback   │
└──────┬──────┘
       ↓
┌─────────────┐
│  Reflector  │ ← 使用Feedback分析方案
└──────┬──────┘
       ↓
┌─────────────┐
│  Insights   │
└──────┬──────┘
       ↓
┌─────────────┐
│   Curator   │ ← 根据Insights更新Playbook
└──────┬──────┘
       ↓
┌─────────────┐
│更新的Playbook│ ← 下次Generator使用
└─────────────┘
```

## 三种评估方式对比

| 特性 | auto | llm_judge | human |
|------|------|-----------|-------|
| 速度 | 快（<1s） | 慢（2-5s） | 很慢（分钟级） |
| 成本 | 免费 | ~0.10元/次 | 人力成本 |
| 准确性 | 低（仅格式） | 高（内容质量） | 最高 |
| 可扩展性 | 高 | 高 | 低 |
| **推荐场景** | **开发调试** | **playbook训练** | **关键方案** |

## 快速使用

### 方式1：环境变量配置

```bash
# 添加到.env文件
EVALUATION_MODE=auto

# 运行ACE
python examples/run_simple_ace.py
```

### 方式2：代码中使用

```python
from evaluation.evaluator import evaluate_plan

# Auto评估（快速、免费）
feedback = evaluate_plan(plan, source="auto")

# LLM评估（准确、消耗tokens）
feedback = evaluate_plan(plan, source="llm_judge", llm_provider=llm)
```

## 运行示例

```bash
# 使用auto评估（默认，快速免费）
python examples/run_simple_ace.py

# 使用LLM评估（更准确，消耗tokens）
EVALUATION_MODE=llm_judge python examples/run_simple_ace.py
```

**预期输出**：
```
[6/9] 评估生成的方案...
  → 使用 'auto' 模式评估...
  ✓ 自动评估完成: 0.87

  评分详情:
    - completeness: 1.00
    - safety: 0.90
    - clarity: 0.80
    - executability: 0.80
    - cost_effectiveness: 0.70
  评论: 方案质量良好，可进一步完善
```

## 评估标准

1. **completeness（完整性）**：是否包含所有必需部分
2. **safety（安全性）**：安全提示是否充分
3. **clarity（清晰度）**：描述是否清晰
4. **executability（可执行性）**：是否可实际执行
5. **cost_effectiveness（成本效益）**：成本是否合理

## 成本对比（qwen-max）

```
单次ACE运行：

Generator:  1500 tokens × 0.12 / 1000 = 0.18元
Evaluator:  800 tokens × 0.12 / 1000 = 0.10元  ← auto模式免费！
Reflector:  2000 tokens × 0.12 / 1000 = 0.24元
Curator:    1200 tokens × 0.12 / 1000 = 0.14元

auto模式总计：  0.56元/次
llm_judge总计： 0.66元/次（+18%）
```

## 推荐策略

### 开发阶段（调试prompt、测试功能）
```bash
EVALUATION_MODE=auto
```
- 快速迭代
- 零额外成本
- 足以发现格式问题

### 训练阶段（改进playbook）
```bash
EVALUATION_MODE=llm_judge
```
- 准确评估质量
- 提供有价值的insights
- 适合playbook进化

### 生产阶段（实际使用）
```python
# 混合策略：auto筛选 + llm_judge复评
auto_fb = evaluate_plan(plan, "auto")
if auto_fb.overall_score < 0.7:
    feedback = evaluate_plan(plan, "llm_judge", llm)
else:
    feedback = auto_fb
```

## 常见问题

**Q: 必须要评估吗？**
A: 是的。没有评估，Reflector无法工作，playbook无法进化。

**Q: 评估会增加多少成本？**
A: auto模式免费；llm_judge约+18%成本（0.10元/次）

**Q: 评估准确吗？**
A: auto模式只检查格式；llm_judge接近人类判断；human最准确

**Q: 可以自定义评估标准吗？**
A: 可以！编辑`configs/ace_config.yaml`的`evaluation_criteria`

## 详细文档

- 完整实现：`src/evaluation/evaluator.py`
- 详细说明：`docs/EVALUATION_SYSTEM.md`
- 配置文件：`configs/ace_config.yaml`
- 使用示例：`examples/run_simple_ace.py`

---

**总结**：反馈来自评估系统，有3种方式（auto/llm_judge/human），推荐开发用auto，训练用llm_judge。
