# ACE Workflow理解修正总结

## ❌ 之前的错误理解

我之前认为ACE三个角色是**顺序执行**的生成流程：

```
Requirements + Templates → Generator → Reflector → Curator → Final Plan
```

这是**完全错误**的！

## ✅ 正确理解

ACE是一个**playbook进化机制**，不是生成流程。分为两个独立的阶段：

### 阶段1：生产环境（实时生成）

```
Requirements + Templates + Playbook → Generator → Experiment Plan ✅
```

**只有Generator参与**，Reflector和Curator不参与。

### 阶段2：训练环境（离线/在线学习）

```
Experiment Plan + Feedback → Reflector → Insights → Curator → Updated Playbook
                                                                      ↓
                                            (下次生成时Generator使用更新后的playbook)
```

Reflector和Curator的作用是**改进playbook**，而不是生成方案。

## 关键区别

| 组件 | 面向用户？ | 何时运行？ | 作用 |
|------|----------|----------|------|
| **Generator** | ✅ 是 | 每次生成方案 | 使用playbook生成实验方案 |
| **Reflector** | ❌ 否 | 离线/在线学习 | 分析反馈，提取改进策略 |
| **Curator** | ❌ 否 | 离线/在线学习 | 将insights更新到playbook |
| **Playbook** | N/A | 持续进化 | 知识库，指导Generator |

## 应用场景

### 生产场景（部署后）
```python
# 用户请求生成方案
generator = ExperimentPlanGenerator(playbook_path="chemistry_v1.json")
plan = generator.generate(requirements, templates)
# 直接返回给用户，Reflector/Curator不运行
```

### 训练场景（改进系统）
```python
# 离线训练
trainer = ACETrainer()
for example in training_data:
    plan = generator.generate(example.requirements, example.templates)
    feedback = llm_judge.evaluate(plan)
    insights = reflector.reflect(plan, feedback)  # ← 学习组件
    curator.update(playbook, insights)            # ← 学习组件

# 保存进化后的playbook
trainer.save_playbook("chemistry_v2.json")
```

### 在线学习场景（持续改进）
```python
# 生产环境中也可以启用学习
plan = generator.generate(requirements, templates)
# 返回给用户

# 异步/定期收集反馈并更新playbook
if user_feedback_available:
    insights = reflector.reflect(plan, user_feedback)
    curator.update(playbook, insights)
```

## 修正的文档

已更新以下文件：
- [x] `README.md` - 系统架构图和ACE说明
- [x] `ARCHITECTURE.md` - 数据流程图（分为实时生成和playbook进化两部分）
- [x] `CLAUDE.md` - 项目理解和数据流程
- [x] `QUICKSTART.md` - 开发优先级说明

## 实现影响

基于正确理解，实现ACE时需要：

1. **Generator必须独立可用**（生产环境只需要它）
2. **Reflector和Curator是可选模块**（仅训练时使用）
3. **接口设计要清晰分离**：
   ```python
   # 生产API
   GET /generate_plan  # 只调用Generator

   # 训练API
   POST /train_playbook  # 调用完整ACE循环
   ```

---

**修正时间**: 2025-10-23
**修正原因**: 混淆了生成流程和学习流程
**关键教训**: ACE是让系统自我改进的机制，不是让系统生成方案的流程
