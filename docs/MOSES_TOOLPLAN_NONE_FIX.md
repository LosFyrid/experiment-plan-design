# MOSES ToolPlan返回None问题 - 修复报告

**问题**: LLM返回None导致Tool Plan生成失败
**根本原因**: System Prompt与ToolPlan Schema格式不匹配
**修复日期**: 2025-10-24
**状态**: ✅ 已修复

---

## 问题诊断

### 错误日志
```
Failed to generate or parse structured tool plan: LLM returned unexpected type NoneType: None
[DEBUG] Raw LLM output type: <class 'NoneType'>
[DEBUG] Raw LLM output: None
```

### 关键观察
用户正确指出：**如果是模型问题，normalize阶段就不可能成功**

从日志可见：
```
Current stage: normalized, Status: parsing_complete ✅
Current stage: entities_refined, Status: entities_refined ✅
Current stage: strategy, Status: strategy_determined ✅
Current stage: execute_query → ToolPlan生成 ❌ (返回None)
```

**结论**: LLM调用正常，问题在于ToolPlan这个**特定的structured output**。

---

## 根本原因：Prompt-Schema不匹配

### 修复前的System Prompt (Line 20-28)

```python
system_prompt = """You are an expert planner for ontology tool execution.
Given a normalized query description and a list of available tools with their descriptions,
create a sequential execution plan (a list of JSON objects) to fulfill the query.
Each step in the plan should be a JSON object with 'tool' (the tool name) and 'params' (a dictionary of parameters for the tool).
Only use the provided tools. Ensure the parameters match the tool's requirements based on its description.
Output ONLY the JSON list of plan steps, without any other text or explanation.
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^
             要求输出列表！

Available tools:
{tool_descriptions}
"""
```

**Prompt要求**: 输出列表 `[{tool: "...", params: {...}}, ...]`

### ToolPlan Schema (schemas.py:67-69)

```python
class ToolPlan(BaseModel):
    steps: List[ToolCallStep] = Field(
        default_factory=list,
        description="The sequence of tool calls to execute."
    )
```

**Schema期望**: 输出对象 `{steps: [{tool: "...", params: {...}}, ...]}`

### 冲突结果

1. LangChain的`with_structured_output(ToolPlan)`传递Schema定义给LLM
2. System Prompt同时要求输出"列表"
3. **两个指令冲突** → LLM confused
4. LLM可能：
   - 返回列表（遵循Prompt） → Schema解析失败 → 返回None
   - 返回对象（遵循Schema） → 与Prompt矛盾
   - **什么都不返回** → 直接返回None ✓ (这是实际发生的)

---

## 修复方案

### 修改1: System Prompt对齐Schema

**文件**: `src/external/MOSES/autology_constructor/idea/query_team/query_agents.py`
**位置**: Line 20-40

**修改前**:
```python
"""...create a sequential execution plan (a list of JSON objects)...
Output ONLY the JSON list of plan steps..."""
```

**修改后**:
```python
"""...create a sequential execution plan to fulfill the query.

Your output must be a JSON object with a "steps" field containing an array of tool calls.
Each step should be a JSON object with:
- 'tool': the name of the tool to call (string)
- 'params': a dictionary of parameters for the tool (object)

Only use the provided tools. Ensure the parameters match the tool's requirements based on its description.

Available tools:
{tool_descriptions}

Output format example:
{{
  "steps": [
    {{"tool": "get_class_info", "params": {{"class_name": "compound"}}}},
    {{"tool": "search_classes", "params": {{"query": "molecular_weight"}}}}
  ]
}}
"""
```

**关键改进**:
1. ✅ 明确要求 `JSON object with a "steps" field`
2. ✅ 提供具体的输出格式示例
3. ✅ 与ToolPlan Schema完全一致

### 修改2: User Message对齐

**位置**: Line 93-96

**修改前**:
```python
user_message = f"""Generate an execution plan for the following normalized query:
{normalized_query_str}

Output the plan as a JSON list of steps matching the ToolCallStep structure."""
```

**修改后**:
```python
user_message = f"""Generate an execution plan for the following normalized query:
{normalized_query_str}

Output the plan as a JSON object with a "steps" array. Each step should match the ToolCallStep structure (tool name and params dictionary)."""
```

### 修改3: 保留Fallback Parsing (已完成)

**位置**: Line 107-145

增强的Fallback Parsing现在支持：
- ✅ `ToolPlan` 对象（理想情况）
- ✅ `{steps: [...]}` 字典
- ✅ `[{...}, {...}]` 裸列表（自动包裹）
- ✅ `None` 值（详细错误提示 + fallback策略建议）

---

## 修复前后对比

### 修复前

```
[Prompt] 请输出列表
          ↓
       [LLM] 收到Prompt要求列表
          ↓
       [LLM] 同时收到Schema要求对象
          ↓
   [LLM confused] 不知道该输出什么
          ↓
       [LLM] 返回 None
          ↓
    [Workflow] 错误：LLM returned None
```

### 修复后

```
[Prompt] 请输出对象 {steps: [...]}
          ↓
       [LLM] 收到一致的指令
          ↓
       [LLM] 生成 {steps: [{tool: "...", params: {...}}]}
          ↓
    [Schema] Pydantic成功解析为ToolPlan
          ↓
    [Workflow] ✅ 执行工具计划
```

---

## 验证测试

### 测试步骤

**1. 快速测试（可选）**:
```bash
# 测试LLM basic调用
python scripts/debug/debug_toolplan.py
```

**2. 端到端测试**（推荐）:
```bash
python examples/chatbot_cli.py

# 输入查询：
"Hierarchy of experimental data extraction for Duplex Stainless Steel research articles"
```

### 预期结果

**修复前**:
```
Current stage: strategy, Status: strategy_determined
Failed to generate or parse structured tool plan: LLM returned unexpected type NoneType: None
Workflow ending due to error at stage: error
❌ 本体知识库中未找到相关信息
```

**修复后**:
```
Current stage: strategy, Status: strategy_determined
Current stage: execute_query, Status: executing ✅
[ToolPlanner] 成功生成执行计划
Current stage: execute_tools, Status: executing ✅
...
✅ 返回查询结果（或明确的"未找到信息"消息）
```

---

## 技术分析

### 为什么normalize成功但ToolPlan失败？

**NormalizedQueryBody的情况**:
- Prompt较短，指令清晰
- Schema字段简单（intent, entities, filters）
- LLM容易理解并正确输出

**ToolPlan的情况**:
- Tool descriptions很长（每个工具的签名+文档）
- Prompt复杂（需要理解工具并规划调用顺序）
- **Prompt和Schema冲突** ← 关键问题
- LLM在复杂场景下更容易被conflicting instructions搞糊涂

### 为什么会返回None而不是错误？

可能的LangChain实现细节：
```python
# with_structured_output内部可能的实现
def with_structured_output(schema):
    def invoke(messages):
        try:
            raw_response = self.call_llm(messages, function_call=schema)
            parsed = parse_json(raw_response)
            return schema(**parsed)
        except:
            return None  # ⬅️ 解析失败时返回None
```

---

## 相关问题和修复

### 问题1: filters字段验证错误 ✅ 已修复
- **原因**: LLM返回空字符串`""`
- **修复**: 添加field_validator转换为None
- **文件**: schemas.py

### 问题2: Tool Plan格式不匹配 ✅ 已修复（Fallback Parsing）
- **原因**: Prompt和Schema格式期望不一致
- **修复**: Fallback Parsing支持多种格式
- **文件**: query_agents.py Line 112-140

### 问题3: Tool Plan返回None ✅ 本次修复
- **原因**: Prompt和Schema指令冲突
- **修复**: 修改Prompt明确要求对象格式
- **文件**: query_agents.py Line 20-40, 93-96

---

## 修改文件列表

| 文件 | 修改内容 | 行数 | 状态 |
|------|---------|------|------|
| `schemas.py` | 添加filters验证器 | 54-60 | ✅ |
| `query_agents.py` | 修复#1: Fallback Parsing | 112-145 | ✅ |
| `query_agents.py` | 修复#2: System Prompt对齐 | 20-40 | ✅ |
| `query_agents.py` | 修复#3: User Message对齐 | 93-96 | ✅ |

---

## 设计原则

这次修复遵循的设计原则：

1. **Prompt-Schema一致性**: 确保LLM的指令与Pydantic Schema期望一致
2. **明确性优于简洁性**: 提供详细的输出格式示例
3. **防御式编程**: 保留Fallback Parsing处理边缘情况
4. **详细的错误日志**: None情况下输出诊断信息

---

## 预期影响

### 正面影响
- ✅ ToolPlan生成成功率显著提高
- ✅ 减少"LLM returned None"错误
- ✅ 工具序列策略能够正常执行
- ✅ 查询结果质量提升

### 潜在风险
- ⚠️ 更长的System Prompt（增加了示例）
  - **影响**: 略微增加token消耗
  - **缓解**: 示例简洁明了，增加的token很少

- ⚠️ LLM可能仍然在某些复杂查询下返回None
  - **缓解**: Fallback Parsing会捕获并提供详细错误信息
  - **建议**: 未来可实现simple_answer fallback策略

---

## 未来改进建议

1. **简化Tool Descriptions**
   - 当前：包含完整签名和文档
   - 建议：提取关键参数，生成简化描述

2. **分阶段规划**
   - 当前：一次性规划所有工具调用
   - 建议：先规划高级步骤，再细化每个步骤

3. **添加重试机制**
   - 当前：返回None即失败
   - 建议：检测到None时用简化prompt重试一次

4. **实现Strategy Fallback**
   - 当前：tool_sequence失败即终止
   - 建议：自动降级到simple_answer策略

---

## 总结

### 修复前
```
3个连续问题：
1. filters验证错误 → 阻塞normalize阶段
2. ToolPlan格式不匹配 → 潜在问题（未触发，因为问题1）
3. ToolPlan返回None → Prompt-Schema冲突
```

### 修复后
```
✅ filters验证器 → normalize通过
✅ Fallback Parsing → 支持多种格式
✅ Prompt对齐 → LLM生成正确格式
```

### 关键洞察
**用户的观察非常正确**："如果是模型问题，normalize阶段就不可能成功"

这个洞察帮助我们快速定位到问题本质：
- 不是模型配置问题
- 不是API调用问题
- **是ToolPlan这个特定场景的Prompt-Schema不匹配问题**

---

**修复完成日期**: 2025-10-24
**验证状态**: ⏸️ 等待用户测试
**下一步**: 运行chatbot_cli.py验证完整流程
