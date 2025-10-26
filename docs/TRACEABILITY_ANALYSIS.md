# 实验方案追溯性分析报告

**调研日期**: 2025-10-26
**问题**: 生成的实验方案能否追踪到使用了什么 bullets 和 RAG 片段？

---

## 📊 调研结果总结

### ✅ 对于 Playbook Bullets - 已实现完整追踪

#### 1. 数据结构支持

**位置**: `src/ace_framework/playbook/schemas.py`

```python
class GenerationResult(BaseModel):
    generated_plan: ExperimentPlan
    trajectory: List[TrajectoryStep] = Field(default_factory=list)
    relevant_bullets: List[str] = Field(
        default_factory=list,
        description="IDs of playbook bullets used"
    )
    generation_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Model name, temperature, tokens, etc."
    )
```

#### 2. 提取机制

**位置**: `src/ace_framework/generator/generator.py` 第273-276行

```python
# Step 8: Extract bullet references
bullets_used_from_output = reasoning_data.get("bullets_used", [])
bullets_used_from_text = extract_bullet_references(response.content)
bullets_used = list(set(bullets_used_from_output + bullets_used_from_text))
```

**双重提取策略**:
1. **LLM 自报告**: 从 LLM 输出的 JSON 中读取 `reasoning.bullets_used` 字段
2. **正则提取**: 从生成的文本中搜索 `[bullet-id]` 或 `(bullet-id)` 模式

**正则模式** (`src/ace_framework/generator/prompts.py` 第309行):
```python
def extract_bullet_references(text: str) -> List[str]:
    # Pattern: [section-NNNNN] or (section-NNNNN)
    pattern = r'[\[\(]([a-z]+-\d{5})[\]\)]'
    matches = re.findall(pattern, text)
    return list(set(matches))
```

#### 3. 存储的元数据

**位置**: `src/ace_framework/generator/generator.py` 第285-292行

```python
generation_metadata={
    "model": response.model,
    "prompt_tokens": response.prompt_tokens,
    "completion_tokens": response.completion_tokens,
    "total_tokens": response.total_tokens,
    "retrieved_bullets_count": len(relevant_bullets),  # 检索到的数量
    "retrieved_bullet_ids": [b.id for b in relevant_bullets],  # 检索到的IDs
    "duration": total_duration
}
```

**区分两个概念**:
- `retrieved_bullet_ids`: 检索阶段获取的所有 bullets（放入 prompt 的）
- `relevant_bullets`: 实际被使用的 bullets（从 LLM 输出提取的）

#### 4. Prompt 引导

**位置**: `src/ace_framework/generator/prompts.py` SYSTEM_PROMPT

LLM 被明确要求在输出中报告使用的 bullets：

```json
{
  "plan": { ... },
  "reasoning": {
    "trajectory": [...],
    "bullets_used": ["mat-00001", "proc-00005"]  ← 要求 LLM 报告
  }
}
```

#### 5. 用于 ACE 训练循环

- **Reflector** 可以分析哪些 bullets 有帮助/有害
- **Curator** 可以更新 bullet 的 `helpful_count`/`harmful_count`
- **统计分析** 可以识别最常用/最有价值的 bullets

---

### ❌ 对于 RAG 模板片段 - 当前缺失追踪

#### 1. 当前状态

**检索到但未记录**:
- ✅ Templates 被检索（`RAGAdapter.retrieve_templates()`）
- ✅ Templates 被保存到文件（`task.save_templates(templates)`）
- ✅ Templates 数量被记录（`generation_metadata` 中的计数）
- ❌ **没有记录**：哪些 templates 实际被使用
- ❌ **没有机制**：让 LLM 报告使用了哪些 template

#### 2. 数据流分析

```python
# Step 1: RAG 检索（task_worker.py）
templates = rag_adapter.retrieve_templates(requirements, top_k=5)
# templates = [
#     {"title": "文献 1: ...", "content": "...", "score": 0.256},
#     {"title": "文献 2: ...", "content": "...", "score": 0.204},
#     ...
# ]

# Step 2: 保存到文件
task.save_templates(templates)  # 保存到 templates.json

# Step 3: Generator 使用
generation_result = generator.generate(
    requirements=requirements,
    templates=templates  # 传入 templates
)

# Step 4: 格式化到 prompt（prompts.py）
formatted = format_templates(templates)
# 放入 prompt 的 "## Reference Templates" 部分

# Step 5: LLM 生成
# ❌ 问题：LLM 没有被要求报告使用了哪些 template
# ❌ 问题：template 没有唯一 ID，无法引用
```

#### 3. 缺失的环节

**问题 A: Template 没有唯一 ID**
```python
# 当前格式
{
    "title": "文献 1: ...",
    "content": "...",
    "score": 0.256
}

# 缺少：template_id 或 doc_id
```

**问题 B: Prompt 没有引导 LLM 报告使用**

当前 SYSTEM_PROMPT 要求：
```json
{
  "reasoning": {
    "bullets_used": ["mat-00001", "proc-00005"]  ← 只要求报告 bullets
    // 没有 templates_used 字段
  }
}
```

**问题 C: 没有提取机制**

`extract_bullet_references()` 只提取 bullet IDs，没有对应的 `extract_template_references()`。

---

## 🔍 差距对比

| 特性 | Playbook Bullets | RAG Templates |
|------|-----------------|---------------|
| **唯一 ID** | ✅ 有（`mat-00001`等） | ❌ 无 |
| **LLM 报告使用** | ✅ 要求在 `reasoning.bullets_used` 中 | ❌ 未要求 |
| **正则提取** | ✅ `extract_bullet_references()` | ❌ 无 |
| **记录检索到的** | ✅ `retrieved_bullet_ids` | ⚠️ 仅数量 |
| **记录实际使用的** | ✅ `relevant_bullets` | ❌ 无 |
| **用于反馈循环** | ✅ Reflector 可分析 | ❌ 无法分析 |

---

## 💡 解决方案设计

### 方案 A: 完整追踪（推荐）

#### 修改 1: 为 Template 添加唯一 ID

**位置**: `src/workflow/rag_adapter.py` 中的 `_convert_to_template_format()`

```python
def _convert_to_template_format(self, docs: List[Dict]) -> List[Dict]:
    templates = []
    for i, doc in enumerate(docs, 1):
        # 生成唯一 ID（使用索引或 doc_hash）
        template_id = f"template-{i:03d}"  # 或 doc.get("metadata", {}).get("doc_hash", f"t{i}")

        template = {
            "id": template_id,  # ← 新增
            "title": f"文献 {i}: {text[:50]}...",
            "content": doc.get("text", ""),
            "score": doc.get("score", 0.0),
        }
        templates.append(template)

    return templates
```

#### 修改 2: 更新 Prompt 格式化

**位置**: `src/ace_framework/generator/prompts.py` 中的 `format_templates()`

```python
def format_templates(templates: List[Dict]) -> str:
    lines = []
    for i, template in enumerate(templates, 1):
        lines.append(f"\n### Template {i}")

        # 显示 ID（如果有）
        if "id" in template:
            lines.append(f"**ID**: {template['id']}")  # ← 新增

        if "title" in template:
            lines.append(f"**Title**: {template['title']}")

        # ... 其他字段
```

#### 修改 3: 更新 SYSTEM_PROMPT

**位置**: `src/ace_framework/generator/prompts.py`

```python
SYSTEM_PROMPT = """
...
Output your response as a JSON object with the following structure:
```json
{
  "plan": { ... },
  "reasoning": {
    "trajectory": [...],
    "bullets_used": ["mat-00001", "proc-00005"],
    "templates_used": ["template-001", "template-002"]  // ← 新增
  }
}
```
"""
```

#### 修改 4: 提取 Template 引用

**位置**: `src/ace_framework/generator/prompts.py`（新增函数）

```python
def extract_template_references(text: str) -> List[str]:
    """
    Extract template IDs referenced in generated text.

    Looks for patterns like [template-001] or (template-001).
    """
    import re
    pattern = r'[\[\(](template-\d{3})[\]\)]'
    matches = re.findall(pattern, text)
    return list(set(matches))
```

#### 修改 5: Generator 提取和存储

**位置**: `src/ace_framework/generator/generator.py`

```python
# Step 8: Extract bullet references
bullets_used_from_output = reasoning_data.get("bullets_used", [])
bullets_used_from_text = extract_bullet_references(response.content)
bullets_used = list(set(bullets_used_from_output + bullets_used_from_text))

# ← 新增：提取 template 引用
templates_used_from_output = reasoning_data.get("templates_used", [])
templates_used_from_text = extract_template_references(response.content)
templates_used = list(set(templates_used_from_output + templates_used_from_text))

# Step 9: Create result
generation_result = GenerationResult(
    generated_plan=experiment_plan,
    trajectory=trajectory,
    relevant_bullets=bullets_used,
    generation_metadata={
        ...
        "retrieved_bullets_count": len(relevant_bullets),
        "retrieved_bullet_ids": [b.id for b in relevant_bullets],
        "retrieved_templates_count": len(templates),  # ← 新增
        "retrieved_template_ids": [t.get("id", f"t{i}") for i, t in enumerate(templates, 1)],  # ← 新增
        "templates_used": templates_used,  # ← 新增
        "duration": total_duration
    },
    timestamp=datetime.now()
)
```

---

### 方案 B: 轻量级追踪（最小修改）

**只记录检索到的 templates，不要求 LLM 报告使用**

#### 修改点

**位置**: `src/ace_framework/generator/generator.py`

```python
generation_metadata={
    ...
    "templates_retrieved": [
        {
            "title": t.get("title", ""),
            "score": t.get("score", 0),
            "content_preview": t.get("content", "")[:100]  # 前100字符
        }
        for t in templates
    ],
}
```

**优点**:
- 修改最小
- 至少记录了检索到的 templates

**缺点**:
- 无法知道哪些 templates 实际被使用
- 无法用于反馈循环优化

---

## 📊 现有数据流可视化

### 当前状态（Bullets 有追踪，Templates 无）

```
┌─────────────────────────────────────────────────────────────┐
│ Step 1: 检索                                                 │
├─────────────────────────────────────────────────────────────┤
│ Playbook Bullets: [mat-00001, mat-00002, proc-00001]        │
│ RAG Templates: [template-1, template-2, template-3]         │
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 2: 格式化到 Prompt                                      │
├─────────────────────────────────────────────────────────────┤
│ ## Playbook Guidance                                         │
│ - [mat-00001] Always verify reagent purity...               │
│ - [mat-00002] Use high-quality solvents...                  │
│                                                               │
│ ## Reference Templates                                       │
│ ### Template 1  ← 没有 ID                                    │
│ **Content**: ...                                             │
│ ### Template 2                                               │
│ **Content**: ...                                             │
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 3: LLM 生成                                             │
├─────────────────────────────────────────────────────────────┤
│ {                                                            │
│   "plan": { ... },                                           │
│   "reasoning": {                                             │
│     "bullets_used": ["mat-00001"]  ← 报告了使用的 bullets   │
│     // 没有 templates_used 字段                             │
│   }                                                          │
│ }                                                            │
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 4: 提取和存储                                           │
├─────────────────────────────────────────────────────────────┤
│ GenerationResult:                                            │
│   relevant_bullets: ["mat-00001"]  ✅ 追踪到了              │
│   generation_metadata:                                       │
│     retrieved_bullet_ids: [...]   ✅ 记录了检索             │
│     // 没有 templates_used 字段    ❌ 缺失                  │
│     // 只有 num_templates: 3       ⚠️ 仅数量                │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 实施建议

### 优先级 1: 方案 B（轻量级追踪）

**原因**:
- 立即可用，无需等待 LLM 行为变化
- 至少记录了检索到的 templates
- 为调试和分析提供基础数据

**工作量**: ~30 分钟（修改 1 处代码）

### 优先级 2: 方案 A（完整追踪）

**原因**:
- 支持未来的 template 质量分析
- 为 RAG 检索优化提供反馈
- 与 bullet 追踪机制一致

**工作量**: ~2-3 小时（修改 5 处代码 + 测试）

**前置条件**:
- 需要先验证 LLM 是否能可靠地报告 template 使用
- 可能需要调整 prompt engineering

---

## 🔄 用途分析

### Bullets 追踪的用途（已实现）

1. **Reflector 分析**: 哪些 bullets 有帮助/有害
2. **Curator 更新**: 增加/减少 helpful_count
3. **统计分析**: 识别最有价值的 bullets
4. **调试**: 理解 Generator 决策过程
5. **可解释性**: 向用户展示使用了哪些指导原则

### Templates 追踪的潜在用途（如果实现）

1. **RAG 质量评估**: 哪些 templates 最有用
2. **检索优化**: 调整检索策略和参数
3. **模板库管理**: 识别高价值模板
4. **调试**: 理解 template 对生成的影响
5. **可解释性**: 向用户展示参考了哪些文献

---

## ✅ 验证方法

### 现有 Bullets 追踪验证

```bash
# 运行 workflow
python examples/workflow_cli.py

# 查看生成结果
cat logs/generation_tasks/{task_id}/plan.json | jq '.relevant_bullets'
# 输出: ["mat-00001", "proc-00005"]

cat logs/generation_tasks/{task_id}/plan.json | jq '.generation_metadata.retrieved_bullet_ids'
# 输出: ["mat-00001", "mat-00002", "proc-00001", ...]
```

### Templates 追踪验证（如果实现方案 B）

```bash
cat logs/generation_tasks/{task_id}/plan.json | jq '.generation_metadata.templates_retrieved'
# 输出: [
#   {"title": "文献 1", "score": 0.256, "content_preview": "..."},
#   ...
# ]
```

---

## 📝 结论

**回答原问题**:

> 最终生成的实验方案能否追踪到使用了什么 bullets 和 RAG 片段？

- **Playbook Bullets**: ✅ **可以**，已有完整的追踪机制
  - 通过 `GenerationResult.relevant_bullets` 字段
  - 双重提取（LLM 报告 + 正则提取）
  - 区分"检索到的"和"实际使用的"

- **RAG Templates**: ❌ **当前不能**，但可以轻松实现
  - 方案 B（轻量级）：30 分钟可完成
  - 方案 A（完整）：2-3 小时可完成

**建议**:
1. 先实施方案 B，快速获得基础追踪能力
2. 后续根据需要升级到方案 A

---

**调研完成日期**: 2025-10-26
**调研者**: Claude Code
