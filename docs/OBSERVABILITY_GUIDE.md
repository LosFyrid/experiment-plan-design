# ACE Framework 可观测性与干预指南

本文档详细说明系统的观测点、干预点和调试策略。

---

## 📊 可观测性层级

### 当前实现状态

```
观测维度          | 实现状态 | 可观测程度 | 改进建议
-----------------|---------|-----------|----------
**数据流追踪**    | 🟡 部分  | 中等      | 添加结构化日志
**性能监控**      | 🔴 无    | 低        | 添加计时器和指标
**错误追踪**      | 🟡 部分  | 中等      | 集中化错误处理
**Playbook演化**  | 🟢 完整  | 高        | 可视化工具
**LLM调用监控**   | 🟡 部分  | 中等      | 添加token/cost追踪
**组件输出**      | 🟢 完整  | 高        | 已有结构化输出
```

---

## 🔍 观测点详解

### 1. Generator观测点

#### 输入观测
```python
# 位置: generator.generate()
{
  "requirements": {...},           # 用户需求
  "templates": [...],              # RAG检索的模板
  "section_filter": [...]          # 筛选的Playbook section
}
```

**观测方法**:
```python
# 当前: 无日志
# 建议: 添加日志记录
logger.info(f"Generator input: requirements={requirements.keys()}, "
            f"templates_count={len(templates or [])}, "
            f"section_filter={section_filter}")
```

#### 中间过程观测
```python
# 步骤1: Bullet检索
relevant_bullets = self._retrieve_bullets(requirements, section_filter)

# 观测点1: 检索到的bullets
print(f"Retrieved {len(relevant_bullets)} bullets")
for bullet, similarity in relevant_bullets[:5]:  # 打印top-5
    print(f"  - {bullet.id}: {bullet.content[:50]}... (sim={similarity:.3f})")

# 步骤2: 提示词构建
user_prompt = build_generation_prompt(
    requirements=requirements,
    playbook_bullets=relevant_bullets,
    templates=templates,
    few_shot_examples=few_shot_examples
)

# 观测点2: 提示词长度
print(f"Prompt length: {len(user_prompt)} chars")
# 建议: 保存到文件用于调试
with open(f"logs/prompts/generator_{timestamp}.txt", "w") as f:
    f.write(user_prompt)

# 步骤3: LLM调用
response = self.llm.generate(prompt=user_prompt, system_prompt=SYSTEM_PROMPT)

# 观测点3: LLM响应
print(f"LLM response length: {len(response)} chars")
print(f"Tokens used: {self.llm.last_token_count}")  # 如果有token统计
```

#### 输出观测
```python
# 位置: GenerationResult
result = GenerationResult(
    generated_plan=plan,            # 生成的实验方案
    relevant_bullets=bullet_ids,    # 使用的bullet IDs
    trajectory=trajectory,          # 推理轨迹
    metadata={
        "tokens_used": tokens,
        "generation_time": elapsed,
        "model": model_name
    }
)

# 观测方法:
print(f"Generated plan: {result.generated_plan.title}")
print(f"Materials: {len(result.generated_plan.materials)}")
print(f"Procedure steps: {len(result.generated_plan.procedure)}")
print(f"Bullets used: {result.relevant_bullets}")
print(f"Trajectory steps: {len(result.trajectory)}")
```

**当前问题**:
- ❌ 无结构化日志（只有print语句）
- ❌ 无提示词保存（难以调试LLM输出）
- ❌ 无性能计时（不知道瓶颈在哪）
- ❌ 无token统计（无法估算成本）

---

### 2. Reflector观测点

#### 输入观测
```python
# 位置: reflector.reflect()
{
  "generated_plan": ExperimentPlan,  # Generator的输出
  "feedback": Feedback,              # 评估结果
  "trajectory": List[TrajectoryStep],# Generator推理过程
  "playbook_bullets_used": List[str] # 使用的bullet IDs
}
```

#### 迭代refinement过程（核心观测点）

```python
# 步骤1: 初始reflection
initial_output = self._perform_initial_reflection(...)

# 观测点1: 初始insights
print(f"Initial reflection: {len(initial_output['insights'])} insights")
for insight in initial_output['insights']:
    print(f"  - [{insight['priority']}] {insight['type']}: {insight['description'][:50]}...")

# 步骤2: 迭代refinement (max 5 rounds)
for round_num in range(2, self.config.max_refinement_rounds + 1):
    refined_output = self._refine_insights(
        previous_output=previous_output,
        round_num=round_num
    )

    # 观测点2: 每轮refinement的改进
    print(f"\n--- Refinement Round {round_num} ---")
    print(f"Insights count: {len(refined_output['insights'])}")
    print(f"Quality improvement indicators:")
    print(f"  - High priority: {count_by_priority['high']}")
    print(f"  - Medium priority: {count_by_priority['medium']}")
    print(f"  - Low priority: {count_by_priority['low']}")

    # 观测点3: Insight内容变化
    # 建议: 保存每轮输出对比
    with open(f"logs/reflections/round_{round_num}.json", "w") as f:
        json.dump(refined_output, f, indent=2)
```

#### Bullet tagging观测
```python
# 步骤3: Bullet tagging
bullet_tags = self._extract_bullet_tags(final_output)

# 观测点4: Bullet使用情况
helpful_count = sum(1 for tag in bullet_tags.values() if tag == BulletTag.HELPFUL)
harmful_count = sum(1 for tag in bullet_tags.values() if tag == BulletTag.HARMFUL)
neutral_count = sum(1 for tag in bullet_tags.values() if tag == BulletTag.NEUTRAL)

print(f"\nBullet Tagging Results:")
print(f"  Helpful: {helpful_count}")
print(f"  Harmful: {harmful_count}")
print(f"  Neutral: {neutral_count}")

for bullet_id, tag in bullet_tags.items():
    print(f"  {bullet_id}: {tag.value}")
```

**当前问题**:
- ⚠️ 有print输出但无结构化记录
- ❌ 无refinement过程的diff对比（无法验证是否真的改进）
- ❌ 无质量指标量化（如insight specificity, actionability）

---

### 3. Curator观测点（最关键！）

#### Delta operations生成

```python
# 步骤1: 生成delta operations
delta_operations = self._generate_delta_operations(
    insights=reflection_result.insights,
    id_prefixes=id_prefixes
)

# 观测点1: Delta operations详情
print(f"\n=== Delta Operations ===")
add_ops = [op for op in delta_operations if op.operation == "ADD"]
update_ops = [op for op in delta_operations if op.operation == "UPDATE"]
remove_ops = [op for op in delta_operations if op.operation == "REMOVE"]

print(f"ADD: {len(add_ops)} operations")
for op in add_ops:
    print(f"  + [{op.new_bullet.section}] {op.new_bullet.content[:50]}...")

print(f"UPDATE: {len(update_ops)} operations")
for op in update_ops:
    print(f"  ~ {op.bullet_id}: {op.new_bullet.content[:50]}...")

print(f"REMOVE: {len(remove_ops)} operations")
for op in remove_ops:
    print(f"  - {op.bullet_id}: {op.reason}")
```

#### Deduplication观测（ACE §3.2核心）

```python
# 步骤2: Semantic deduplication
dedup_report = self._perform_deduplication()

# 观测点2: Deduplication详情
print(f"\n=== Deduplication Report ===")
print(f"Total deduplicated: {dedup_report.total_deduplicated}")
print(f"Similarity threshold: {self.config.deduplication_threshold}")

for merge in dedup_report.merges:
    print(f"Merge: {merge['kept_bullet']} ← {merge['removed_bullet']}")
    print(f"  Similarity: {merge['similarity']:.3f}")
    print(f"  Kept helpfulness: {merge['kept_helpfulness']:.2f}")
    print(f"  Removed helpfulness: {merge['removed_helpfulness']:.2f}")
```

#### Playbook演化观测（最重要！）

```python
# 步骤3: Playbook before/after对比
print(f"\n=== Playbook Evolution ===")
print(f"Before: {playbook_before.size} bullets")
print(f"After: {playbook_after.size} bullets")
print(f"Net change: {playbook_after.size - playbook_before.size:+d}")

# 观测点3: Section分布变化
print("\nSection Distribution:")
for section in playbook_after.sections:
    before_count = len(playbook_before.get_bullets_by_section(section))
    after_count = len(playbook_after.get_bullets_by_section(section))
    print(f"  {section}: {before_count} → {after_count} ({after_count - before_count:+d})")

# 观测点4: Metadata统计
print("\nMetadata Statistics:")
avg_helpfulness_before = sum(b.metadata.helpfulness_score for b in playbook_before.bullets) / playbook_before.size
avg_helpfulness_after = sum(b.metadata.helpfulness_score for b in playbook_after.bullets) / playbook_after.size
print(f"  Avg helpfulness: {avg_helpfulness_before:.3f} → {avg_helpfulness_after:.3f}")

# 观测点5: 新增bullets的来源
new_bullets = [b for b in playbook_after.bullets if b.metadata.source == "reflection"]
print(f"\nNew bullets from reflection: {len(new_bullets)}")
for bullet in new_bullets:
    print(f"  + {bullet.id}: {bullet.content[:60]}...")
```

**当前实现**:
- 🟢 已有print输出（curator.py:165-498）
- 🟢 PlaybookUpdateResult包含完整统计
- ⚠️ 但缺少结构化保存（无法追踪历史）

---

## 🎛️ 干预点详解

### Tier 1: 配置级干预（最常用，无需改代码）

#### 1.1 Generator干预

```yaml
# configs/ace_config.yaml
generator:
  top_k_bullets: 50              # ← 干预: 减少/增加检索的bullets数量
  enable_templates: true         # ← 干预: 开关RAG template
  include_examples: false        # ← 干预: 开关few-shot learning
  output_format: "json"          # ← 干预: 切换JSON/Markdown输出
  min_similarity: 0.3            # ← 干预: Bullet检索相似度阈值
```

**效果**:
- `top_k_bullets` ↑ → 更多上下文，但prompt更长，成本更高
- `min_similarity` ↑ → 更严格筛选，可能遗漏相关bullets
- `enable_templates: false` → 测试Playbook单独的效果

#### 1.2 Reflector干预

```yaml
reflector:
  enable_iterative: true         # ← 干预: 开关迭代refinement
  max_refinement_rounds: 5       # ← 干预: 调整refinement轮数 (1-5)
  enable_bullet_tagging: true    # ← 干预: 开关bullet tagging
  require_ground_truth: false    # ← 干预: 是否需要ground truth对比
```

**效果**:
- `max_refinement_rounds: 1` → 跳过迭代，测试初始reflection质量
- `max_refinement_rounds: 5` → 最大化insight质量（论文默认）
- `enable_bullet_tagging: false` → 禁止Playbook学习（只提取insights）

#### 1.3 Curator干预（核心！）

```yaml
curator:
  update_mode: "incremental"     # ← 干预: incremental vs lazy
  enable_grow_and_refine: true   # ← 干预: 开关deduplication
  deduplication_threshold: 0.85  # ← 干预: 相似度阈值 (0-1)
  max_playbook_size: 200         # ← 干预: Playbook最大size
  pruning_threshold: 0.3         # ← 干预: Helpfulness阈值（低于会被删除）
```

**效果**:
- `update_mode: "lazy"` → 只在超过max_size时deduplicate（更快）
- `deduplication_threshold` ↑ (e.g., 0.95) → 更严格，只删除几乎完全相同的
- `deduplication_threshold` ↓ (e.g., 0.75) → 更激进，可能错删有用的
- `max_playbook_size: 100` → 强制更频繁pruning
- `pruning_threshold: 0.5` → 更激进删除表现不好的bullets

#### 1.4 Model干预

```yaml
model:
  provider: "qwen"              # ← 干预: 切换provider
  model_name: "qwen-max"        # ← 干预: qwen-max vs qwen-plus vs qwen-turbo
  temperature: 0.7              # ← 干预: 0=deterministic, 1=creative
  max_tokens: 4000              # ← 干预: 输出长度限制
  top_p: 0.95                   # ← 干预: nucleus sampling
```

**⚠️ 重要**: 所有三个角色应使用**相同模型**（论文§4.2）

---

### Tier 2: 数据级干预（手动编辑）

#### 2.1 Playbook直接编辑

```bash
# 编辑Playbook文件
vim data/playbooks/chemistry_playbook.json

# 可以:
# - 添加seed bullets (高质量起点)
# - 删除有害bullets (人工审核后)
# - 修改bullet内容 (纠正错误)
# - 调整metadata (修正helpfulness_score)
```

**使用场景**:
- **冷启动**: 添加领域专家知识作为seed
- **质量控制**: 人工审核后删除明显错误的bullets
- **A/B测试**: 创建不同版本的Playbook对比

#### 2.2 Prompt直接修改

```bash
# 修改Generator prompts
vim src/ace_framework/generator/prompts.py

# 修改Reflector prompts
vim src/ace_framework/reflector/prompts.py

# 修改Curator prompts
vim src/ace_framework/curator/prompts.py
```

**⚠️ 注意**: 按照之前的"何时修改prompt"指南，只改domain-specific部分

#### 2.3 Mock Feedback调整

```python
# 在examples/ace_cycle_example.py中
feedback = Feedback(
    scores=[
        FeedbackScore(criterion="completeness", score=0.8, ...),
        FeedbackScore(criterion="safety", score=0.7, ...),  # ← 干预: 调整评分
        # ... 添加更多criteria
    ],
    overall_score=0.81,  # ← 干预: 调整总分
    feedback_source="auto"
)
```

**使用场景**:
- 测试Reflector对不同feedback的响应
- 模拟极端情况（全部高分/全部低分）
- 验证特定criterion的影响

---

### Tier 3: 代码级干预（高级调试）

#### 3.1 添加断点调试

```python
# 在generator.py中
def generate(self, requirements, templates, ...):
    relevant_bullets = self._retrieve_bullets(...)

    # 干预点1: 检查检索结果
    import pdb; pdb.set_trace()  # 断点

    user_prompt = build_generation_prompt(...)

    # 干预点2: 检查提示词
    import pdb; pdb.set_trace()

    response = self.llm.generate(...)

    # 干预点3: 检查LLM响应
    import pdb; pdb.set_trace()
```

#### 3.2 添加hook函数

```python
# 在generator.py的__init__中
self.before_generate_hook = None  # 用户可注入
self.after_generate_hook = None

def generate(self, ...):
    if self.before_generate_hook:
        self.before_generate_hook(requirements, templates)

    result = ...  # 正常生成

    if self.after_generate_hook:
        self.after_generate_hook(result)

    return result

# 使用:
def my_hook(result):
    print(f"Custom logging: {result.generated_plan.title}")
    # 保存到自定义日志系统

generator.after_generate_hook = my_hook
```

#### 3.3 Replay机制（未实现，建议）

```python
# 建议: 保存每次生成的完整输入/输出
class ReplayableGenerator(PlanGenerator):
    def generate(self, ...):
        # 保存输入
        with open(f"logs/replays/{timestamp}_input.json", "w") as f:
            json.dump({
                "requirements": requirements,
                "templates": templates,
                "config": self.config.dict()
            }, f)

        result = super().generate(...)

        # 保存输出
        with open(f"logs/replays/{timestamp}_output.json", "w") as f:
            json.dump(result.dict(), f)

        return result

# 好处: 可以重放任意历史生成，用于:
# - Bug复现
# - 模型对比（重放同样输入到不同模型）
# - Prompt优化（重放同样输入到不同prompt版本）
```

---

## 🛠️ 推荐的可观测性增强方案

### 优先级1: 结构化日志

```python
# 创建: src/utils/logger.py
import logging
import json
from pathlib import Path
from datetime import datetime

class StructuredLogger:
    """结构化日志记录器，支持JSON输出和查询"""

    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)

        # 创建分类日志
        self.generator_log = self.log_dir / "generator.jsonl"
        self.reflector_log = self.log_dir / "reflector.jsonl"
        self.curator_log = self.log_dir / "curator.jsonl"

    def log_generation(self, event_type: str, data: dict):
        """记录Generator事件"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "component": "generator",
            "event_type": event_type,  # "bullet_retrieval", "llm_call", "output"
            "data": data
        }
        with open(self.generator_log, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def log_reflection(self, event_type: str, data: dict):
        """记录Reflector事件"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "component": "reflector",
            "event_type": event_type,  # "initial", "refinement_round", "bullet_tagging"
            "data": data
        }
        with open(self.reflector_log, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def log_curation(self, event_type: str, data: dict):
        """记录Curator事件"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "component": "curator",
            "event_type": event_type,  # "delta_ops", "deduplication", "pruning"
            "data": data
        }
        with open(self.curator_log, "a") as f:
            f.write(json.dumps(entry) + "\n")

# 使用:
logger = StructuredLogger()
logger.log_generation("bullet_retrieval", {
    "query": requirements["objective"],
    "bullets_retrieved": len(relevant_bullets),
    "top_5_similarities": [sim for _, sim in relevant_bullets[:5]]
})
```

### 优先级2: Playbook版本追踪

```python
# 创建: src/utils/playbook_versioning.py
import json
import shutil
from pathlib import Path
from datetime import datetime

class PlaybookVersionTracker:
    """追踪Playbook演化历史"""

    def __init__(self, playbook_path: str, versions_dir: str = "data/playbook_versions"):
        self.playbook_path = Path(playbook_path)
        self.versions_dir = Path(versions_dir)
        self.versions_dir.mkdir(exist_ok=True)

    def save_version(self, reason: str, metadata: dict = None):
        """保存当前Playbook版本快照"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        version_file = self.versions_dir / f"playbook_{timestamp}.json"

        # 复制Playbook
        shutil.copy(self.playbook_path, version_file)

        # 保存元数据
        meta_file = self.versions_dir / f"meta_{timestamp}.json"
        with open(meta_file, "w") as f:
            json.dump({
                "timestamp": timestamp,
                "reason": reason,
                "metadata": metadata or {}
            }, f, indent=2)

        return version_file

    def diff_versions(self, version1: str, version2: str):
        """对比两个Playbook版本"""
        with open(version1) as f:
            pb1 = json.load(f)
        with open(version2) as f:
            pb2 = json.load(f)

        bullets1 = {b["id"]: b for b in pb1["bullets"]}
        bullets2 = {b["id"]: b for b in pb2["bullets"]}

        added = set(bullets2.keys()) - set(bullets1.keys())
        removed = set(bullets1.keys()) - set(bullets2.keys())
        modified = {
            bid for bid in bullets1.keys() & bullets2.keys()
            if bullets1[bid]["content"] != bullets2[bid]["content"]
        }

        return {
            "added": list(added),
            "removed": list(removed),
            "modified": list(modified),
            "size_change": len(bullets2) - len(bullets1)
        }

# 使用:
tracker = PlaybookVersionTracker(playbook_path)
tracker.save_version(
    reason="After ACE cycle",
    metadata={
        "generation_id": gen_id,
        "feedback_score": 0.81,
        "insights_count": 3
    }
)
```

### 优先级3: 性能监控

```python
# 创建: src/utils/performance_monitor.py
import time
from contextlib import contextmanager
from typing import Dict, List
import json

class PerformanceMonitor:
    """性能监控器"""

    def __init__(self):
        self.metrics: Dict[str, List[float]] = {}

    @contextmanager
    def measure(self, operation: str):
        """测量操作耗时"""
        start = time.time()
        try:
            yield
        finally:
            elapsed = time.time() - start
            if operation not in self.metrics:
                self.metrics[operation] = []
            self.metrics[operation].append(elapsed)

    def report(self):
        """生成性能报告"""
        report = {}
        for operation, times in self.metrics.items():
            report[operation] = {
                "count": len(times),
                "total": sum(times),
                "avg": sum(times) / len(times),
                "min": min(times),
                "max": max(times)
            }
        return report

    def save(self, path: str):
        """保存性能数据"""
        with open(path, "w") as f:
            json.dump(self.report(), f, indent=2)

# 使用:
perf = PerformanceMonitor()

with perf.measure("bullet_retrieval"):
    relevant_bullets = self._retrieve_bullets(...)

with perf.measure("llm_generation"):
    response = self.llm.generate(...)

with perf.measure("output_parsing"):
    plan = ExperimentPlan(**parsed)

# 最后:
perf.save("logs/performance.json")
print(perf.report())
```

---

## 📈 可观测性最佳实践

### 1. 关键事件必须记录

```python
# Generator
✓ Bullet检索 (数量、相似度分布)
✓ LLM调用 (输入/输出token数、耗时)
✓ 输出解析 (成功/失败)

# Reflector
✓ 每轮refinement (insights数量、优先级分布)
✓ Bullet tagging (helpful/harmful/neutral统计)

# Curator
✓ Delta operations (ADD/UPDATE/REMOVE各几个)
✓ Deduplication (删除了几个、相似度分布)
✓ Pruning (删除了几个、原因)
✓ Playbook size变化 (before/after)
```

### 2. 错误必须可追溯

```python
# 当前问题: 只有print警告
print(f"Warning: Failed to parse JSON: {e}")

# 改进: 保存完整错误上下文
logger.error("JSON parsing failed", extra={
    "raw_response": response,
    "error": str(e),
    "traceback": traceback.format_exc(),
    "prompt": user_prompt,  # ← 关键! 可以重放
    "config": self.config.dict()
})
```

### 3. 中间结果可导出

```python
# 每个组件应支持导出中间状态
result = generator.generate(...)

# 导出选项1: 完整JSON
result.export("logs/generations/gen_20250123_143022.json")

# 导出选项2: 人类可读
result.export_human_readable("logs/generations/gen_20250123_143022.md")

# 内容应包括:
# - 输入 (requirements, templates)
# - 中间步骤 (bullets检索, prompt构建)
# - LLM交互 (request, response)
# - 输出 (parsed plan)
# - Metadata (tokens, time, config)
```

### 4. 支持时间范围查询

```bash
# 查询过去24小时的Playbook变化
python scripts/query_logs.py --component curator \
    --event-type deduplication \
    --since "2025-01-23 00:00:00" \
    --format table

# 输出:
# Timestamp            | Deduplicated | Avg Similarity | Playbook Size
# ---------------------|--------------|----------------|---------------
# 2025-01-23 10:30:15  | 3            | 0.91           | 47 → 44
# 2025-01-23 14:22:08  | 1            | 0.87           | 50 → 49
```

---

## 🎯 推荐的调试工作流

### 场景1: Generator输出质量不好

```
1. 检查bullet检索
   → 查看logs/generator.jsonl中的bullet_retrieval事件
   → 验证相似度分布是否合理（是否检索到相关bullets?）

2. 检查prompt
   → 导出prompt到logs/prompts/
   → 人工阅读，验证instructions是否清晰
   → 尝试调整top_k_bullets或min_similarity

3. 检查LLM输出
   → 查看logs/generator.jsonl中的llm_call事件
   → 验证是否是parsing错误还是LLM生成质量问题
   → 尝试调整temperature或切换模型
```

### 场景2: Playbook增长过快

```
1. 检查delta operations
   → 查看logs/curator.jsonl中的delta_ops事件
   → 统计ADD操作占比（是否每次都添加大量bullets?）

2. 检查deduplication
   → 查看logs/curator.jsonl中的deduplication事件
   → 验证threshold是否过高（导致无法删除相似bullets）
   → 尝试降低deduplication_threshold (e.g., 0.85 → 0.80)

3. 启用更激进pruning
   → 调整configs/ace_config.yaml:
     curator:
       max_playbook_size: 100  # 降低上限
       pruning_threshold: 0.4  # 提高pruning阈值
```

### 场景3: Refinement没有改进insights

```
1. 导出每轮refinement输出
   → 使用logger.log_reflection保存每轮输出
   → 人工对比round 1 vs round 5的insights

2. 验证prompt是否有效
   → 检查prompts.py中的REFINEMENT_SYSTEM_PROMPT
   → 确认是否清楚指示"improve specificity and actionability"

3. 尝试不同refinement轮数
   → max_refinement_rounds: 1 (baseline)
   → max_refinement_rounds: 3
   → max_refinement_rounds: 5
   → 对比质量差异
```

---

## 📊 可视化工具（建议实现）

### 1. Playbook演化可视化

```python
# scripts/visualize_playbook_evolution.py
import matplotlib.pyplot as plt
import json
from pathlib import Path

def plot_evolution(versions_dir: str):
    versions = sorted(Path(versions_dir).glob("playbook_*.json"))

    sizes = []
    avg_helpfulness = []
    timestamps = []

    for version_file in versions:
        with open(version_file) as f:
            playbook = json.load(f)

        sizes.append(len(playbook["bullets"]))

        helpfulness_scores = [
            b["metadata"]["helpful_count"] / max(b["metadata"]["total_uses"], 1)
            for b in playbook["bullets"]
        ]
        avg_helpfulness.append(sum(helpfulness_scores) / len(helpfulness_scores))

        # 从文件名提取时间
        timestamp = version_file.stem.split("_", 1)[1]
        timestamps.append(timestamp)

    # 绘图
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))

    ax1.plot(timestamps, sizes, marker='o')
    ax1.set_title("Playbook Size Over Time")
    ax1.set_ylabel("Number of Bullets")

    ax2.plot(timestamps, avg_helpfulness, marker='o', color='green')
    ax2.set_title("Average Helpfulness Score Over Time")
    ax2.set_ylabel("Helpfulness Score")

    plt.tight_layout()
    plt.savefig("logs/playbook_evolution.png")
    print("Saved to logs/playbook_evolution.png")

# 使用:
plot_evolution("data/playbook_versions")
```

### 2. Bullet热力图

```python
# 可视化哪些bullets被频繁使用
def plot_bullet_heatmap(playbook_path: str):
    with open(playbook_path) as f:
        playbook = json.load(f)

    # 按section分组，统计total_uses
    section_usage = {}
    for bullet in playbook["bullets"]:
        section = bullet["section"]
        uses = bullet["metadata"]["total_uses"]

        if section not in section_usage:
            section_usage[section] = []
        section_usage[section].append(uses)

    # 绘制heatmap
    # (实现略)
```

---

## ✅ 总结：快速可观测性检查清单

在运行ACE循环后，检查以下内容：

- [ ] **Generator日志**: 检查检索到的bullets数量和相似度
- [ ] **Reflector日志**: 查看每轮refinement的insights数量
- [ ] **Curator日志**: 确认delta operations类型和数量
- [ ] **Deduplication报告**: 验证是否有重复bullets被合并
- [ ] **Playbook文件**: 对比before/after，确认size变化合理
- [ ] **Playbook版本**: 保存快照，便于回滚
- [ ] **性能数据**: 检查哪个步骤最耗时
- [ ] **错误日志**: 查看是否有parsing或LLM调用失败

当前最需要的改进:
1. 🔴 添加结构化日志（StructuredLogger）
2. 🔴 实现Playbook版本追踪（PlaybookVersionTracker）
3. 🟡 添加性能监控（PerformanceMonitor）
4. 🟡 实现可视化工具

这些改进可以让你更好地理解和调试ACE框架的运行状态！
