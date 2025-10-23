# ACE框架观测性改进方案

本文档列出所有可行的观测性改进方案，供选择实施。

---

## 方案总览

| ID | 方案名称 | 优先级 | 工作量 | 价值 | 依赖 |
|----|---------|--------|-------|------|------|
| **A1** | 结构化日志系统 | 🔴 高 | 3h | ⭐⭐⭐⭐⭐ | 无 |
| **A2** | Playbook版本追踪 | 🔴 高 | 2h | ⭐⭐⭐⭐⭐ | 无 |
| **A3** | 性能监控系统 | 🟡 中 | 2h | ⭐⭐⭐⭐ | 无 |
| **A4** | LLM调用追踪 | 🔴 高 | 2h | ⭐⭐⭐⭐⭐ | 无 |
| **A5** | 提示词保存与管理 | 🟡 中 | 1h | ⭐⭐⭐⭐ | 无 |
| **B1** | 中间结果导出器 | 🟡 中 | 2h | ⭐⭐⭐⭐ | A1 |
| **B2** | 错误追踪与重放 | 🟢 低 | 3h | ⭐⭐⭐ | A1, A4 |
| **B3** | Delta Operations详细日志 | 🟡 中 | 1h | ⭐⭐⭐⭐ | A1 |
| **B4** | Refinement进度追踪 | 🟡 中 | 1h | ⭐⭐⭐ | A1 |
| **C1** | 指标统计与报告 | 🟡 中 | 2h | ⭐⭐⭐⭐ | A1, A2 |
| **C2** | Playbook健康度检查 | 🟢 低 | 2h | ⭐⭐⭐ | A2 |
| **C3** | 配置版本管理 | 🟢 低 | 1h | ⭐⭐ | 无 |
| **D1** | Playbook演化可视化 | 🟢 低 | 3h | ⭐⭐⭐ | A2, C1 |
| **D2** | 实时监控面板 | 🟢 低 | 5h | ⭐⭐ | A1, A3, C1 |
| **D3** | Bullet热力图 | 🟢 低 | 2h | ⭐⭐⭐ | A2 |

**优先级说明**:
- 🔴 高: 基础设施，其他功能的依赖
- 🟡 中: 重要但非必需，显著提升调试效率
- 🟢 低: 锦上添花，主要用于分析和报告

---

## A类方案：核心基础设施

### A1. 结构化日志系统 🔴

**功能描述**:
- 创建统一的日志记录器，支持JSON格式输出
- 为Generator/Reflector/Curator的关键事件添加日志
- 支持按组件、事件类型、时间范围查询

**能观测什么**:
```python
# Generator事件
- bullet_retrieval: 检索到哪些bullets，相似度分布
- llm_call: LLM请求/响应，token数，耗时
- output_parsing: 解析成功/失败，错误信息
- plan_generated: 生成的plan结构统计

# Reflector事件
- initial_reflection: 初始reflection结果
- refinement_round: 每轮refinement的输出
- bullet_tagging: Bullet的helpful/harmful/neutral标记
- insights_extracted: 提取的insights统计

# Curator事件
- delta_generation: 生成的ADD/UPDATE/REMOVE操作
- deduplication: 检测到的重复bullets
- pruning: 删除的低质量bullets
- playbook_updated: Playbook变化统计
```

**实现内容**:
1. `src/utils/structured_logger.py`: 日志记录器类
2. 在Generator/Reflector/Curator中集成日志调用
3. 查询工具: `scripts/query_logs.py`

**输出示例**:
```json
{
  "timestamp": "2025-01-23T14:30:15.123Z",
  "component": "generator",
  "event_type": "bullet_retrieval",
  "data": {
    "query": "Synthesize aspirin from salicylic acid",
    "bullets_retrieved": 7,
    "top_similarities": [0.87, 0.82, 0.79, 0.75, 0.72, 0.68, 0.65],
    "sections": ["material_selection": 3, "procedure_design": 4]
  }
}
```

**工作量**: ~3小时
- 日志器实现: 1h
- 集成到三个组件: 1.5h
- 查询工具: 0.5h

**价值**: ⭐⭐⭐⭐⭐
- 所有其他方案的基础
- 可追溯所有关键决策
- 支持离线分析和调试

---

### A2. Playbook版本追踪 🔴

**功能描述**:
- 每次Curator更新后自动保存Playbook快照
- 记录每个版本的元数据（原因、时间、统计）
- 支持版本对比和回滚

**能观测什么**:
```python
# 版本历史
- 每个版本的时间戳
- 触发更新的原因（哪次generation）
- Size变化、Section分布变化
- 新增/修改/删除的bullets详情

# 版本对比
- 两个版本之间的diff
- Bullet内容变化
- Metadata变化（helpfulness_score趋势）

# Bullet生命周期
- 某个bullet何时添加
- 何时被修改
- 何时被删除（如果被pruning）
```

**实现内容**:
1. `src/utils/playbook_versioning.py`: 版本追踪器
2. 在Curator的`update()`方法中自动保存版本
3. 对比工具: `scripts/diff_playbook_versions.py`
4. 可视化工具: `scripts/visualize_evolution.py`

**输出示例**:
```
data/playbook_versions/
├── playbook_20250123_143015.json
├── meta_20250123_143015.json  # {"reason": "After ACE cycle", "generation_id": "gen-001"}
├── playbook_20250123_150422.json
├── meta_20250123_150422.json
└── ...

# Diff输出
Version 1 → Version 2:
  Added bullets: mat-00019, proc-00012
  Removed bullets: safe-00003
  Modified bullets: qc-00005 (content changed)
  Size change: 21 → 22 (+1)
```

**工作量**: ~2小时
- 版本追踪器: 1h
- 集成到Curator: 0.5h
- Diff工具: 0.5h

**价值**: ⭐⭐⭐⭐⭐
- 追踪Playbook演化历史
- 支持回滚到任意版本
- 验证ACE学习是否有效

---

### A3. 性能监控系统 🟡

**功能描述**:
- 自动测量每个关键操作的耗时
- 统计LLM API调用的token数和成本
- 生成性能报告

**能观测什么**:
```python
# 耗时统计
- bullet_retrieval: 平均0.2s
- llm_generation: 平均25s (瓶颈!)
- output_parsing: 平均0.1s
- refinement_round_1: 15s
- refinement_round_2: 16s
- ...
- deduplication: 平均1.5s

# Token统计
- Generator平均input tokens: 2500
- Generator平均output tokens: 1200
- Reflector每轮tokens: 1800 input, 800 output
- 单次ACE循环总tokens: ~15000

# 成本估算
- 单次ACE循环成本: ¥0.15 (按Qwen定价)
- 100次循环成本: ¥15
```

**实现内容**:
1. `src/utils/performance_monitor.py`: 性能监控器
2. Context manager装饰器用于自动计时
3. 在Generator/Reflector/Curator中添加计时点
4. 报告生成: `scripts/generate_performance_report.py`

**输出示例**:
```json
{
  "performance_report": {
    "bullet_retrieval": {
      "count": 10,
      "total_time": 2.1,
      "avg_time": 0.21,
      "min_time": 0.18,
      "max_time": 0.35
    },
    "llm_generation": {
      "count": 10,
      "total_time": 253.4,
      "avg_time": 25.34,
      "total_tokens": 35000,
      "estimated_cost_cny": 1.75
    }
  }
}
```

**工作量**: ~2小时
- 监控器实现: 1h
- 集成到组件: 0.5h
- 报告工具: 0.5h

**价值**: ⭐⭐⭐⭐
- 识别性能瓶颈
- 估算运行成本
- 指导优化方向

---

### A4. LLM调用追踪 🔴

**功能描述**:
- 记录所有LLM API调用的完整请求和响应
- 保存prompt、system_prompt、响应内容
- 支持重放历史调用（用于调试）

**能观测什么**:
```python
# 每次LLM调用
- 完整的prompt内容
- System prompt
- 配置参数（temperature, max_tokens, etc.）
- 响应内容（完整原始文本）
- Token统计
- 耗时
- 成功/失败状态
- 错误信息（如果失败）

# 追踪能力
- 查看某次生成使用的exact prompt
- 对比不同版本prompt的效果
- 重放失败的调用进行调试
- A/B测试不同prompt
```

**实现内容**:
1. `src/utils/llm_call_tracker.py`: LLM调用追踪器
2. 在`BaseLLMProvider`中集成追踪逻辑
3. 重放工具: `scripts/replay_llm_call.py`
4. 对比工具: `scripts/compare_prompts.py`

**输出示例**:
```
logs/llm_calls/
├── 20250123_143015_generator_gen-001.json
│   {
│     "timestamp": "2025-01-23T14:30:15Z",
│     "component": "generator",
│     "model": "qwen-max",
│     "config": {"temperature": 0.7, "max_tokens": 4000},
│     "system_prompt": "You are an expert chemistry...",
│     "user_prompt": "# Requirements\n...",
│     "response": "{\"title\": \"Synthesis of Aspirin\",...}",
│     "tokens": {"input": 2500, "output": 1200},
│     "time": 25.3,
│     "status": "success"
│   }
├── 20250123_143045_reflector_round1.json
└── ...
```

**工作量**: ~2小时
- 追踪器实现: 1h
- 集成到LLM Provider: 0.5h
- 重放/对比工具: 0.5h

**价值**: ⭐⭐⭐⭐⭐
- 调试prompt最重要的工具
- 支持重放失败场景
- 验证prompt修改的影响
- 成本分析

---

### A5. 提示词保存与管理 🟡

**功能描述**:
- 自动保存每次生成使用的提示词
- 组织为可读的文件结构
- 支持搜索和对比

**能观测什么**:
```python
# 提示词内容
- 完整的user prompt（包括requirements, bullets, templates）
- System prompt
- Few-shot examples（如果有）

# 提示词分析
- 平均prompt长度
- Bullets使用分布
- Templates使用分布
- 变化趋势（随Playbook演化）
```

**实现内容**:
1. 在Generator/Reflector/Curator中添加prompt保存逻辑
2. 文件组织: `logs/prompts/{component}/{timestamp}.txt`
3. 搜索工具: `scripts/search_prompts.py`

**输出示例**:
```
logs/prompts/
├── generator/
│   ├── 20250123_143015_gen-001.txt
│   ├── 20250123_150422_gen-002.txt
│   └── ...
├── reflector/
│   ├── 20250123_143045_initial.txt
│   ├── 20250123_143052_round2.txt
│   └── ...
└── curator/
    └── ...
```

**工作量**: ~1小时
- 添加保存逻辑: 0.5h
- 搜索工具: 0.5h

**价值**: ⭐⭐⭐⭐
- 人工检查prompt质量
- 验证bullet检索是否合理
- 调试生成问题

---

## B类方案：增强功能

### B1. 中间结果导出器 🟡

**功能描述**:
- 为Generator/Reflector/Curator添加结果导出功能
- 支持JSON和人类可读格式
- 包含所有中间步骤

**能观测什么**:
```python
# Generator导出内容
- 输入: requirements, templates, config
- 中间步骤: bullet检索结果, prompt构建
- LLM交互: request, response
- 输出: 解析后的ExperimentPlan
- Metadata: tokens, time, bullets_used

# Reflector导出内容
- 输入: plan, feedback, trajectory
- 每轮refinement的输出
- Bullet tagging结果
- 最终insights

# Curator导出内容
- 输入: reflection_result
- 生成的delta operations
- Deduplication过程
- Pruning决策
- Playbook before/after
```

**实现内容**:
1. 为每个Result类添加`export()`方法
2. 支持JSON和Markdown格式
3. 自动导出工具: 在example中启用

**输出示例**:
```
logs/exports/
├── gen-001/
│   ├── generation_result.json        # 完整JSON
│   ├── generation_result.md          # 人类可读
│   ├── input.json
│   ├── bullet_retrieval.json
│   └── llm_call.json
├── gen-001_reflection/
│   ├── reflection_result.json
│   ├── round_1.json
│   ├── round_2.json
│   └── ...
└── gen-001_curation/
    ├── update_result.json
    ├── delta_operations.json
    └── deduplication_report.json
```

**工作量**: ~2小时
- 添加export方法: 1h
- 格式化逻辑: 0.5h
- 集成到example: 0.5h

**价值**: ⭐⭐⭐⭐
- 完整保存每次运行
- 便于人工审查
- 支持离线分析

**依赖**: A1（结构化日志）

---

### B2. 错误追踪与重放 🟢

**功能描述**:
- 捕获所有错误和异常
- 保存错误现场（输入、状态、traceback）
- 支持重放错误场景

**能观测什么**:
```python
# 错误信息
- 错误类型和堆栈
- 发生时间和组件
- 完整的输入数据
- 系统状态（config, playbook size, etc.）

# 错误模式
- 哪种错误最常见
- 哪个组件错误最多
- 错误趋势（是否增加）
```

**实现内容**:
1. `src/utils/error_tracker.py`: 错误追踪器
2. 在Generator/Reflector/Curator中添加try-except块
3. 重放工具: `scripts/replay_error.py`

**输出示例**:
```json
{
  "error_id": "err-20250123-143015",
  "timestamp": "2025-01-23T14:30:15Z",
  "component": "generator",
  "error_type": "JSONDecodeError",
  "message": "Expecting value: line 1 column 1 (char 0)",
  "traceback": "...",
  "input": {
    "requirements": {...},
    "templates": [...],
    "config": {...}
  },
  "llm_response": "The synthesis of aspirin...",  # 未包含JSON
  "playbook_state": {
    "size": 21,
    "sections": {...}
  }
}
```

**工作量**: ~3小时
- 错误追踪器: 1.5h
- 集成到组件: 1h
- 重放工具: 0.5h

**价值**: ⭐⭐⭐
- 快速定位问题
- 支持bug复现
- 改进错误处理

**依赖**: A1（日志）, A4（LLM调用追踪）

---

### B3. Delta Operations详细日志 🟡

**功能描述**:
- 为Curator的每个delta operation添加详细日志
- 记录决策依据
- 追踪operation执行结果

**能观测什么**:
```python
# ADD操作
- 添加原因（来自哪个insight）
- 新bullet内容
- 分配的section和ID
- 是否被deduplication拦截

# UPDATE操作
- 更新原因
- 旧内容 vs 新内容
- Metadata变化

# REMOVE操作
- 删除原因（低helpfulness? deduplication? pruning?）
- 被删除的bullet内容
- 最终metadata状态
```

**实现内容**:
1. 在Curator的`_apply_delta_operations()`中添加详细日志
2. 为每个operation类型添加专门的日志函数
3. 统计报告: `scripts/analyze_delta_operations.py`

**输出示例**:
```json
{
  "timestamp": "2025-01-23T14:35:20Z",
  "operation": "ADD",
  "reason": "Insight: best_practice - Add TLC monitoring",
  "new_bullet": {
    "id": "qc-00015",
    "section": "quality_control",
    "content": "Use TLC to monitor esterification progress..."
  },
  "duplicate_check": {
    "is_duplicate": false,
    "closest_match": "qc-00012",
    "similarity": 0.72
  },
  "result": "success"
}
```

**工作量**: ~1小时
- 添加日志逻辑: 0.5h
- 统计工具: 0.5h

**价值**: ⭐⭐⭐⭐
- 理解Playbook如何演化
- 验证Curator决策合理性
- 调试deduplication问题

**依赖**: A1（结构化日志）

---

### B4. Refinement进度追踪 🟡

**功能描述**:
- 追踪Reflector每轮refinement的改进
- 量化insight质量变化
- 可视化refinement过程

**能观测什么**:
```python
# 每轮统计
- Insights数量变化
- 优先级分布变化（high/medium/low）
- Insight类型分布
- 描述长度变化（更具体?）
- Actionability变化

# 质量指标
- Specificity score: 描述是否具体
- Actionability score: 是否可执行
- Novelty score: 是否与已有bullets重复
```

**实现内容**:
1. 在Reflector中添加每轮统计逻辑
2. 质量指标计算器（启发式或LLM-based）
3. 可视化: `scripts/visualize_refinement.py`

**输出示例**:
```
Refinement Progress:
Round 1: 5 insights (high:1, medium:3, low:1), avg_length:45 chars
Round 2: 4 insights (high:2, medium:2, low:0), avg_length:68 chars  ← 更具体
Round 3: 3 insights (high:2, medium:1, low:0), avg_length:82 chars  ← 质量提升
Round 4: 3 insights (high:3, medium:0, low:0), avg_length:95 chars  ← 收敛
Round 5: 3 insights (high:3, medium:0, low:0), avg_length:93 chars

Quality improvement: +85% (Round 1 → Round 5)
```

**工作量**: ~1小时
- 统计逻辑: 0.5h
- 可视化: 0.5h

**价值**: ⭐⭐⭐
- 验证iterative refinement是否有效
- 决定最佳refinement轮数
- 论文实验数据

**依赖**: A1（结构化日志）

---

## C类方案：分析与报告

### C1. 指标统计与报告 🟡

**功能描述**:
- 聚合所有日志生成统计报告
- 支持时间范围、组件、事件类型筛选
- 自动生成Markdown/HTML报告

**能观测什么**:
```python
# 系统级指标
- 总ACE循环次数
- 总token消耗
- 总成本
- 平均每次循环耗时

# Generator指标
- 生成成功率: 95% (95/100)
- 平均bullets使用数: 7.2
- 平均生成时间: 25s
- 平均output tokens: 1200

# Reflector指标
- 平均insights数: 3.5
- Insights质量分布
- 平均refinement轮数: 4.8
- Bullet tagging分布

# Curator指标
- Playbook增长率: +0.5 bullets/cycle
- Deduplication率: 15% (15/100 candidates)
- Pruning触发次数: 3
- 平均更新操作数: 2.3

# Playbook指标
- 当前size: 45 bullets
- 各section分布
- 平均helpfulness_score: 0.72
- Top 10 most used bullets
```

**实现内容**:
1. `src/utils/metrics_aggregator.py`: 指标聚合器
2. 报告生成器: `scripts/generate_report.py`
3. HTML模板（可选）

**输出示例**:
```markdown
# ACE Framework Report
Period: 2025-01-20 to 2025-01-23 (3 days)

## Overview
- Total ACE cycles: 50
- Total tokens consumed: 750K
- Estimated cost: ¥37.5
- Success rate: 96% (48/50)

## Generator Performance
- Avg generation time: 24.5s
- Avg bullets used: 7.2
- Avg output tokens: 1185

## Playbook Evolution
- Size: 18 → 45 (+150%)
- Avg helpfulness: 0.68 → 0.72 (+6%)
- Deduplication events: 8

## Top Insights
1. safety_issue: Missing temperature monitoring (5 occurrences)
2. best_practice: Use TLC for progress tracking (4 occurrences)
...
```

**工作量**: ~2小时
- 聚合器实现: 1h
- 报告生成: 1h

**价值**: ⭐⭐⭐⭐
- 全局视角看系统表现
- 定期review和改进
- 实验数据收集

**依赖**: A1（日志）, A2（Playbook版本）

---

### C2. Playbook健康度检查 🟢

**功能描述**:
- 定期检查Playbook质量
- 识别潜在问题
- 生成健康度报告

**能观测什么**:
```python
# 健康度指标
- Size是否合理（15-200）
- Section分布是否均衡
- 是否有大量低质量bullets（helpfulness < 0.3）
- 是否有从未使用的bullets（total_uses = 0）
- 是否有过度使用的bullets（total_uses > 50）
- 是否有重复bullets（similarity > 0.9）

# 问题识别
⚠️ Warning: 12 bullets with helpfulness < 0.3
⚠️ Warning: 5 bullets never used (might be too specific)
✓ OK: Size within range (45/200)
✓ OK: Section distribution balanced
```

**实现内容**:
1. `src/utils/playbook_health_checker.py`: 健康度检查器
2. 检查规则定义
3. 报告生成: `scripts/check_playbook_health.py`

**输出示例**:
```
Playbook Health Report
======================
Overall Score: 78/100 (Good)

✓ Size: 45/200 (23%) - OK
✓ Section balance: CV=0.15 - OK
⚠️ Low quality bullets: 12 (27%) - Consider pruning
⚠️ Unused bullets: 5 (11%) - Too specific?
✓ No high-similarity duplicates detected
✓ Metadata consistency: OK

Recommendations:
1. Lower pruning_threshold to remove 12 low-quality bullets
2. Review unused bullets: mat-00018, proc-00023, ...
3. Consider splitting large procedure_design section
```

**工作量**: ~2小时
- 检查器实现: 1h
- 规则定义: 0.5h
- 报告生成: 0.5h

**价值**: ⭐⭐⭐
- 主动发现问题
- 优化Playbook质量
- 维护指南

**依赖**: A2（Playbook版本）

---

### C3. 配置版本管理 🟢

**功能描述**:
- 自动保存每次运行使用的配置
- 追踪配置变化历史
- 支持配置对比

**能观测什么**:
```python
# 配置历史
- 每次运行使用的完整配置
- 配置修改时间和原因
- 哪些参数被修改过

# 配置影响分析
- 修改某个参数后的效果
- A/B测试不同配置
- 最优配置寻找
```

**实现内容**:
1. 在每次运行时保存配置快照
2. 对比工具: `scripts/diff_configs.py`
3. 分析工具: `scripts/analyze_config_impact.py`

**输出示例**:
```
configs/snapshots/
├── config_20250123_143015.yaml
├── config_20250123_150422.yaml  # deduplication_threshold: 0.85 → 0.80
└── ...

# Diff输出
Config changes (20250123_143015 → 20250123_150422):
  curator.deduplication_threshold: 0.85 → 0.80

Impact analysis:
  Playbook growth rate: +0.5 → +0.3 bullets/cycle (改善!)
  Deduplication events: 2 → 5 (增加)
```

**工作量**: ~1小时
- 自动保存: 0.5h
- 对比工具: 0.5h

**价值**: ⭐⭐
- 追踪实验参数
- 配置调优
- 可重现性

**依赖**: 无

---

## D类方案：可视化工具

### D1. Playbook演化可视化 🟢

**功能描述**:
- 绘制Playbook size随时间变化
- 绘制平均helpfulness_score趋势
- Section分布变化
- Bullet生命周期可视化

**能观测什么**:
```python
# 时间序列图
- Playbook size曲线
- Helpfulness score曲线
- Token消耗曲线
- 成本曲线

# Section分布图
- 堆叠面积图显示各section占比
- 识别哪些section增长最快

# Bullet生命周期
- 何时添加、何时修改、何时删除
- Helpfulness_score变化轨迹
```

**实现内容**:
1. `scripts/visualize_playbook_evolution.py`
2. 使用matplotlib/plotly绘图
3. 生成PNG/HTML输出

**输出示例**:
```
logs/visualizations/
├── playbook_size_over_time.png
├── helpfulness_trend.png
├── section_distribution.png
└── bullet_lifecycle_mat-00015.png
```

**工作量**: ~3小时
- 数据加载: 0.5h
- 绘图逻辑: 2h
- 多图表集成: 0.5h

**价值**: ⭐⭐⭐
- 直观看到演化趋势
- 识别异常模式
- 论文图表

**依赖**: A2（Playbook版本）, C1（指标统计）

---

### D2. 实时监控面板 🟢

**功能描述**:
- Web界面实时显示系统状态
- 实时日志流
- 性能指标仪表盘

**能观测什么**:
```python
# 实时数据
- 当前正在运行的组件
- 实时token消耗
- 实时错误/警告
- Playbook当前状态

# 仪表盘
- 今日ACE循环次数
- 今日token消耗
- 今日成本
- 成功率
- 平均耗时
```

**实现内容**:
1. Web后端（Flask/FastAPI）
2. 前端仪表盘（HTML+JS）
3. WebSocket实时推送
4. 启动脚本: `python dashboard.py`

**输出示例**:
```
浏览器访问 http://localhost:8080

[Dashboard界面]
┌─────────────────────────────────┐
│ ACE Framework Monitor            │
├─────────────────────────────────┤
│ Status: ● Running (Reflector)   │
│ Playbook Size: 45 bullets       │
│ Today's Cycles: 12              │
│ Today's Cost: ¥0.60            │
├─────────────────────────────────┤
│ [实时日志流]                     │
│ 14:30:15 Generator: Retrieved 7  │
│ 14:30:40 Generator: Plan OK     │
│ 14:30:45 Reflector: Round 1...  │
└─────────────────────────────────┘
```

**工作量**: ~5小时
- 后端API: 2h
- 前端界面: 2h
- 实时推送: 1h

**价值**: ⭐⭐
- 酷炫演示
- 实时监控
- 但非必需

**依赖**: A1（日志）, A3（性能监控）, C1（指标）

---

### D3. Bullet热力图 🟢

**功能描述**:
- 可视化哪些bullets被频繁使用
- 热力图显示section和bullet的使用频率
- 识别"明星bullets"和"僵尸bullets"

**能观测什么**:
```python
# Bullet使用频率
- Top 10 most used bullets
- Top 10 least used bullets
- 各section的活跃度

# 热力图
- X轴: Bullets (按ID排序)
- Y轴: Section
- 颜色: 使用频率
```

**实现内容**:
1. `scripts/visualize_bullet_heatmap.py`
2. 使用seaborn绘制热力图
3. 交互式HTML版本（plotly）

**输出示例**:
```
[热力图显示]
Section              | Bullets Usage Frequency
---------------------|------------------------
material_selection   | ████████░░░░░ (8/12)
procedure_design     | ██████████░░░ (10/15)
safety_protocols     | ████░░░░░░░░░ (4/10)
...

Top 5 Most Used Bullets:
1. mat-00001 (45 uses): "Verify reagent purity..."
2. proc-00005 (38 uses): "Monitor reaction temperature..."
3. qc-00003 (35 uses): "Use TLC to check progress..."
```

**工作量**: ~2小时
- 数据聚合: 0.5h
- 热力图绘制: 1h
- 交互式版本: 0.5h

**价值**: ⭐⭐⭐
- 识别最有价值的bullets
- 清理无用bullets
- 优化Playbook结构

**依赖**: A2（Playbook版本）

---

## 实施建议

### 最小可行方案（MVP）
推荐先实施这些核心功能，工作量约 **9小时**:

1. **A1. 结构化日志系统** (3h) - 基础中的基础
2. **A2. Playbook版本追踪** (2h) - 追踪演化必需
3. **A4. LLM调用追踪** (2h) - 调试prompt必需
4. **A3. 性能监控系统** (2h) - 识别瓶颈

### 标准方案
在MVP基础上，添加增强功能，工作量约 **+6小时**:

5. **A5. 提示词保存与管理** (1h)
6. **B1. 中间结果导出器** (2h)
7. **B3. Delta Operations详细日志** (1h)
8. **C1. 指标统计与报告** (2h)

### 完整方案
包含所有可视化和分析工具，工作量约 **+12小时**:

9. **B4. Refinement进度追踪** (1h)
10. **C2. Playbook健康度检查** (2h)
11. **D1. Playbook演化可视化** (3h)
12. **D3. Bullet热力图** (2h)
13. **B2. 错误追踪与重放** (3h)
14. **C3. 配置版本管理** (1h)

### 豪华方案（可选）
如果需要Web界面，工作量约 **+5小时**:

15. **D2. 实时监控面板** (5h)

---

## 优先级矩阵

```
价值高 │ A1 A2 A4 │ B1 B3    │ C1
      │ A3      │ B4 A5    │ C2
──────┼─────────┼──────────┼────────
价值低 │         │ C3       │ B2 D1 D3 D2
      └─────────┴──────────┴────────
        必需       有用        锦上添花
```

**建议选择策略**:
- **时间紧**: 只做A类（9h），确保基础设施完善
- **时间充裕**: A类 + B类 + C1 (15h)，完整的观测和分析能力
- **追求完美**: 全部实现 (32h)，论文级别的可观测性

---

## 总结

| 类别 | 方案数 | 总工作量 | 核心价值 |
|------|-------|---------|---------|
| **A类 (基础)** | 5 | 10h | 日志、版本、性能、LLM追踪 - 必需 |
| **B类 (增强)** | 4 | 7h | 导出、错误追踪、详细日志 - 提升效率 |
| **C类 (分析)** | 3 | 5h | 统计报告、健康检查 - 全局视角 |
| **D类 (可视化)** | 3 | 10h | 图表、仪表盘 - 直观展示 |
| **总计** | 15 | 32h | 完整的观测性系统 |

**推荐起步**: A1 + A2 + A4 (7小时) → 即可支撑有效测试！

---

*等待你的选择... 你想先实施哪些方案？*
