# MOSES Qwen ToolPlan生成失败问题分析

## 问题描述

从GPT切换到Qwen后，MOSES在第3次重试时出现ToolPlan生成失败：

```
Failed to generate or parse structured tool plan: 1 validation error for ToolPlan
steps
  Input should be a valid list [type=list_type, input_value='\n[{"tool": "parse_hiera..._class_name": null}}]\n', input_type=str]
    For further information visit https://errors.pydantic.dev/2.12/v/list_type
```

## 关键发现

### 1. 问题触发条件
- **发生时机**: retry_count=3 (第3次重试)
- **模型**: qwen3-max
- **API调用成功**: HTTP 200 OK from DashScope
- **Raw LLM output**: not captured (异常发生在structured_llm.invoke()内部)

### 2. Pydantic错误详情

```python
input_value='\n[{"tool": "parse_hiera..._class_name": null}}]\n'
input_type=str
expected_type=list
```

**关键**: `steps`字段收到的是一个**字符串化的JSON数组**，而不是Python list对象。

### 3. 诊断脚本验证结果

运行 `diagnose_qwen_structured_output.py` 显示：
- ✓ Qwen + with_structured_output() 在简单场景下**工作正常**
- ✓ 返回类型正确: `<class '__main__.TestPlan'>`
- ✓ 多次调用一致性良好

这说明问题**不是LangChain与Qwen的兼容性问题**。

## 根本原因推测

### 可能性1: LangGraph状态序列化问题 (最可能)

LangGraph在节点间传递状态时会进行序列化/反序列化。如果：
1. `generate_plan()` 返回一个ToolPlan对象
2. 该对象被LangGraph序列化为JSON字符串存储在state中
3. 下一次读取时，反序列化失败或部分失败
4. 导致某些字段（如`steps`）保持为字符串状态

**证据**:
- 问题发生在第3次重试（多次状态传递后）
- 第1次和第2次重试正常工作
- 错误信息显示收到的是字符串化JSON而非对象

### 可能性2: with_structured_output() 在某些提示下返回异常格式

在复杂的重试场景中，当用户消息包含大量hints和历史信息时：
```python
# 从日志中看到的hints内容
"Previously tried: duplex_stainless_steel, duplex_stainless_steel(DSS), ..."
# 极长的类名列表
```

可能导致：
- Token limit接近上限
- LLM输出格式略有不同
- LangChain的结构化输出解析器fallback到不同的策略

**证据**:
- 发生在重试次数较多时
- Hints内容累积很长
- `raw_plan`变量未被捕获（说明异常在invoke内部）

### 可能性3: Pydantic模型验证时机问题

`with_structured_output(ToolPlan)` 内部会调用Pydantic验证。如果：
1. LLM返回的JSON中`steps`字段被包裹在字符串中
2. LangChain的解析器没有正确unwrap
3. 直接传给Pydantic验证导致类型错误

**证据**:
- Pydantic错误信息明确显示收到了字符串
- `input_value='\n[{"tool": "parse_hiera...'` 显示JSON被字符串化

## 对比：GPT vs Qwen

### GPT模式下的工作机制
```python
# GPT使用原生OpenAI接口
ChatOpenAI(
    model_name="gpt-4.1-mini",
    openai_api_key=api_key
)
```

### Qwen模式下的工作机制
```python
# Qwen使用OpenAI兼容接口
ChatOpenAI(
    model="qwen-plus",  # 注意：参数名是model而不是model_name
    api_key=dashscope_api_key,
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)
```

**关键差异**:
1. API endpoint不同
2. 模型响应格式可能有细微差别
3. Function calling / Structured output实现可能不同

## 解决方案方向

### 方案1: 在generate_plan()中添加字符串解析fallback

```python
# 在query_agents.py:124之后添加
raw_plan = structured_llm.invoke(messages)

# NEW: 检查是否为dict且steps为字符串
if isinstance(raw_plan, dict) and "steps" in raw_plan:
    if isinstance(raw_plan["steps"], str):
        import json
        try:
            # 尝试解析字符串化的JSON
            raw_plan["steps"] = json.loads(raw_plan["steps"])
            print(f"[ToolPlanner] Fixed stringified steps field")
        except json.JSONDecodeError as e:
            print(f"[ToolPlanner] Failed to parse stringified steps: {e}")
```

### 方案2: 使用method='json_mode'

```python
# 在query_agents.py:123
structured_llm = self._get_structured_llm(ToolPlan)
# 改为
structured_llm = self.model_instance.with_structured_output(
    ToolPlan,
    method="json_mode"
)
```

诊断脚本显示这种模式也工作正常。

### 方案3: 禁用LangGraph的自动序列化

修改QueryState定义，让execution_plan字段不被序列化：

```python
# stategraph.py
execution_plan: Optional[ToolPlan]  # 当前
# 改为
execution_plan: Optional[Any]  # 避免Pydantic序列化
```

但这可能影响其他功能。

### 方案4: 添加重试机制中的plan对象类型检查

```python
# query_workflow.py:286-292
plan_result = tool_planner_agent.generate_plan(...)

# 添加类型验证
if isinstance(plan_result, dict) and "steps" in plan_result:
    if isinstance(plan_result["steps"], str):
        # 自动修复
        plan_result["steps"] = json.loads(plan_result["steps"])
```

## 下一步行动

1. **立即实施方案1** - 最安全，向后兼容
2. **添加更详细的调试日志** - 在query_agents.py:123-124之间打印raw_plan的完整内容
3. **测试json_mode** - 验证方案2是否能解决问题
4. **检查LangGraph版本** - 可能是特定版本的bug

## 相关文件

- `/src/external/MOSES/autology_constructor/idea/query_team/query_agents.py:72-169`
- `/src/external/MOSES/autology_constructor/idea/query_team/query_workflow.py:286-296`
- `/src/external/MOSES/autology_constructor/idea/query_team/schemas.py:62-69`
- `/src/external/MOSES/autology_constructor/idea/common/base_agent.py:51-60`

## 测试用例

已创建:
- `scripts/debug/diagnose_qwen_structured_output.py` - 基础兼容性测试 ✓
- `scripts/debug/diagnose_moses_toolplan_issue.py` - MOSES场景模拟测试 (待运行)

建议添加:
- 重试场景集成测试
- 长prompt+hints的压力测试
- LangGraph状态序列化测试
