# MOSES Tool Plan Generation Failure Analysis

## Error Summary
The error "Failed to generate or parse structured tool plan: LLM did not return a list structure as expected for the plan." occurs when the ToolPlannerAgent fails to generate a properly structured ToolPlan object.

---

## 1. Error Source Location

**File**: `/home/syk/projects/experiment-plan-design/src/external/MOSES/autology_constructor/idea/query_team/query_agents.py`

**Line 125**: Error message generation
```python
except Exception as e:
    # Catch errors during structured output generation/parsing or validation
    error_msg = f"Failed to generate or parse structured tool plan: {str(e)}"
    print(f"{error_msg}")
    return {"error": error_msg}
```

**Line 115**: Direct trigger for the error message
```python
if not isinstance(plan, ToolPlan):
    raise ValueError("LLM did not return a list structure as expected for the plan.")
```

---

## 2. ToolPlan Schema Definition

**File**: `/home/syk/projects/experiment-plan-design/src/external/MOSES/autology_constructor/idea/query_team/schemas.py`

**Lines 62-69**:
```python
class ToolCallStep(BaseModel):
    """Represents a single step in a tool execution plan."""
    tool: str = Field(description="The name of the tool to be called. Must be one of the available OntologyTools methods.")
    params: Dict[str, Any] = Field(default_factory=dict, description="A dictionary of parameters required to call the specified tool.")

class ToolPlan(BaseModel):
    """Represents the planned sequence of tool calls."""
    steps: List[ToolCallStep] = Field(default_factory=list, description="The sequence of tool calls to execute.")
```

**Key Structure**:
- `ToolPlan` is a Pydantic BaseModel
- Contains a `steps` field (List of ToolCallStep objects)
- Each step has:
  - `tool`: string (tool name)
  - `params`: dictionary (parameters for the tool)

---

## 3. Tool Plan Generation Function

**File**: `/home/syk/projects/experiment-plan-design/src/external/MOSES/autology_constructor/idea/query_team/query_agents.py`

**Lines 58-130**: `ToolPlannerAgent.generate_plan()` method

### Method Signature:
```python
def generate_plan(self, 
                  normalized_query: Union[Dict, NormalizedQuery], 
                  ontology_tools: OntologyTools, 
                  tool_hints: List = None) -> Union[ToolPlan, Dict]:
```

### Key Steps:

1. **Input Validation** (Lines 60-64):
   - Checks if normalized_query is missing or contains error
   - Returns error dict if invalid

2. **Tool Description Generation** (Line 66):
   - Calls `_get_tool_descriptions(ontology_tools)` (Lines 36-56)
   - Extracts available tools from OntologyTools instance using reflection
   - Filters out private methods and specific excluded methods

3. **Prompt Construction** (Lines 69-100):
   - Formats system prompt with tool descriptions
   - Creates user message with normalized query
   - Optionally adds tool hints section

4. **LLM Invocation** (Lines 107-110):
   ```python
   structured_llm = self._get_structured_llm(ToolPlan)
   plan: ToolPlan = structured_llm.invoke(messages)
   ```
   - Gets structured LLM configured for ToolPlan output
   - Invokes LLM with messages

5. **Validation** (Lines 113-115):
   - Checks if returned object is ToolPlan instance
   - This is where the error is triggered if validation fails

6. **Entity Correction** (Lines 117-119):
   - Validates and fixes class names in plan parameters
   - Uses `_validate_and_fix_plan_entities()` method

---

## 4. LLM System Prompt

**File**: `/home/syk/projects/experiment-plan-design/src/external/MOSES/autology_constructor/idea/query_team/query_agents.py`

**Lines 20-28**:
```python
system_prompt = """You are an expert planner for ontology tool execution.
Given a normalized query description and a list of available tools with their descriptions, 
create a sequential execution plan (a list of JSON objects) to fulfill the query.
Each step in the plan should be a JSON object with 'tool' (the tool name) and 'params' 
(a dictionary of parameters for the tool).
Only use the provided tools. Ensure the parameters match the tool's requirements based on its description.
Output ONLY the JSON list of plan steps, without any other text or explanation.

Available tools:
{tool_descriptions}
"""
```

**Important**: The prompt explicitly asks for:
- A **list of JSON objects** (not a single object with a `steps` field)
- Each object with `tool` and `params` fields
- Output **ONLY** the JSON, without extra text

---

## 5. Structured Output Configuration

**File**: `/home/syk/projects/experiment-plan-design/src/external/MOSES/autology_constructor/idea/common/base_agent.py`

**Lines 51-60**: `_get_structured_llm()` method
```python
def _get_structured_llm(self, pydantic_schema: Type[T]):
    """Returns an LLM instance configured for structured output with the given Pydantic schema."""
    if not self.model_instance:
        raise ValueError(f"Model instance not available in agent '{self.name}' to configure structured output.")
    try:
        return self.model_instance.with_structured_output(pydantic_schema)
    except Exception as e:
        raise RuntimeError(f"Failed to configure structured output for schema {pydantic_schema.__name__} in agent '{self.name}': {e}") from e
```

---

## 6. Root Cause Analysis

### Primary Issue: Mismatch Between Prompt and Schema

The **critical problem** is a **mismatch between the LLM's expected output format (from the system prompt) and the structured output schema**:

1. **Prompt says**: "Output ONLY the JSON **list** of plan steps"
   - Expects: `[{tool: "...", params: {...}}, {tool: "...", params: {...}}]`

2. **Schema expects**: A `ToolPlan` object with a `steps` field
   - Expects: `{steps: [{tool: "...", params: {...}}, ...]}`

3. **What likely happens**:
   - LLM generates the list format as instructed by the prompt
   - LangChain's structured output parser tries to wrap/parse it as ToolPlan
   - Parsing fails because the LLM output doesn't match the schema structure
   - The returned object is not a valid ToolPlan instance
   - Line 113's validation fails
   - Error message is generated

### Secondary Issues:

1. **Tool Description Filtering** (Line 45):
   - Excluded tools: `["__init__", "execute_sparql", "get_class_richness_info"]`
   - This limits what tools the planner can use

2. **Error Handling** (Lines 123-130):
   - Broad exception catching loses original error details
   - Returns error dict instead of raising, which breaks the workflow
   - The workflow expects Union[ToolPlan, Dict], but dict case triggers error in execute_query (line 296)

3. **No Fallback Parsing** (Lines 107-115):
   - If structured output fails, no attempt to parse raw LLM output
   - No logging of what the LLM actually returned

---

## 7. Call Stack - Where Tool Plan Generation is Used

**File**: `/home/syk/projects/experiment-plan-design/src/external/MOSES/autology_constructor/idea/query_team/query_workflow.py`

**Lines 283-296**: `execute_query()` node function
```python
# Generate execution plan
if tool_related_hints:
    plan_result = tool_planner_agent.generate_plan(
        normalized_query_obj, 
        ontology_tools, 
        tool_hints=tool_related_hints  # Line 289
    )
else:
    plan_result = tool_planner_agent.generate_plan(normalized_query_obj, ontology_tools)

# Check for errors
if isinstance(plan_result, dict) and plan_result.get("error"):
    raise ValueError(f"Failed to generate tool plan: {plan_result.get('error')}")  # Line 296
elif not isinstance(plan_result, Union[ToolPlan, Dict]):
    raise TypeError(f"Tool planner returned unexpected type: {type(plan_result)}")
```

The workflow **catches the error dict** and raises a ValueError, which then triggers the `except` block (line 361) that returns an error state.

---

## 8. Expected List Structure

Based on the schema and prompt, here's what should be returned:

### Schema Structure (What LangChain expects):
```python
{
    "steps": [
        {
            "tool": "tool_name_1",
            "params": {
                "param1": "value1",
                "param2": "value2"
            }
        },
        {
            "tool": "tool_name_2",
            "params": {
                "class_names": ["class1", "class2"]
            }
        }
    ]
}
```

### What Prompt Instructs LLM to Output:
```json
[
    {
        "tool": "tool_name_1",
        "params": {
            "param1": "value1",
            "param2": "value2"
        }
    },
    {
        "tool": "tool_name_2",
        "params": {
            "class_names": ["class1", "class2"]
        }
    }
]
```

**The difference**: One is wrapped with `"steps": [...]`, the other is a bare array.

---

## 9. Why the Validation Fails (Line 113)

The validation at line 113 checks:
```python
if not isinstance(plan, ToolPlan):
    raise ValueError("LLM did not return a list structure as expected for the plan.")
```

This fails because:

1. LLM generates output in list format (as per prompt): `[{...}, {...}]`
2. LangChain's `with_structured_output()` tries to parse it as ToolPlan
3. Parsing can fail if:
   - The LLM includes extra text around the JSON
   - The LLM changes the structure
   - The LLM forgets to wrap it properly
   - The LLM model doesn't support structured output well
4. When parsing fails, `structured_llm.invoke()` either:
   - Returns None or invalid object
   - Returns dict instead of ToolPlan
   - Raises an exception (caught at line 123)

---

## 10. Key Code Flows

### Flow 1: Normal Path (Happy Case)
```
normalize_query() 
  → QueryParserAgent → NormalizedQuery ✓
determine_strategy() 
  → StrategyPlannerAgent → "tool_sequence" ✓
execute_query()
  → ToolPlannerAgent.generate_plan() → ToolPlan ✓
  → ToolExecutorAgent.execute_plan() → execution results ✓
validate_results()
  → ValidationAgent → ValidationReport ✓
```

### Flow 2: Error Path (Tool Plan Generation Fails)
```
execute_query()
  → ToolPlannerAgent.generate_plan()
    → _get_structured_llm(ToolPlan) creates structured LLM
    → structured_llm.invoke(messages) fails
    → Exception caught at line 123
    → Returns {"error": "Failed to generate or parse structured tool plan: ..."}
  → Line 296 checks plan_result.get("error") 
  → Raises ValueError
  → Caught at line 361 (outer try-except)
  → Returns error state with stage="error"
```

---

## 11. Summary of Issues

| Component | Issue | Impact |
|-----------|-------|--------|
| **System Prompt** | Asks for bare array instead of wrapped object | LLM output doesn't match schema |
| **Schema Validation** | Checks `isinstance(plan, ToolPlan)` | Fails when LLM returns list instead of object |
| **Error Handling** | Returns dict instead of raising | Breaks workflow expectations |
| **LLM Configuration** | No error details captured | Hard to debug what LLM returned |
| **Structured Output** | No fallback parsing logic | Complete failure on format mismatch |
| **Tool Filtering** | Excludes some tools from planner | Limited planning capabilities |

---

## 12. Files Involved

1. **`query_agents.py`** (Lines 17-192): ToolPlannerAgent class and generate_plan method
2. **`schemas.py`** (Lines 62-69): ToolPlan and ToolCallStep Pydantic models
3. **`base_agent.py`** (Lines 51-60): _get_structured_llm helper method
4. **`query_workflow.py`** (Lines 283-296): Call to generate_plan in execute_query node

---

## 13. Configuration Context

From `configs/ace_config.yaml`:
- Uses Qwen LLM (qwen-max)
- Generator configured with playbook retrieval (top-50 bullets)
- Reflector supports iterative refinement (max 5 rounds)
- Curator uses incremental delta updates

The tool plan generation should be compatible with Qwen's structured output capabilities.

