# Tool Plan Generation Failure - Executive Summary

## Quick Reference

**Error Message**:
```
Failed to generate or parse structured tool plan: LLM did not return a list structure as expected for the plan.
```

**Root Cause**: 
Prompt-Schema Mismatch - The system prompt instructs the LLM to output a bare JSON list, but the ToolPlan Pydantic schema expects the list wrapped in a `{steps: [...]}` object.

**Status**: IDENTIFIED & DOCUMENTED

---

## Files to Review

1. **TOOL_PLAN_ANALYSIS.md** - Complete 13-section analysis
2. **TOOL_PLAN_CODE_SNIPPETS.md** - All relevant code excerpts with line numbers
3. This document - Executive summary

---

## The Problem in 30 Seconds

The ToolPlannerAgent tries to generate a structured execution plan using an LLM:

1. **System Prompt says** (line 20-28 in query_agents.py):
   > "Output ONLY the JSON **list** of plan steps"
   
   Expects: `[{tool: "...", params: {...}}, ...]`

2. **ToolPlan Schema says** (line 67-69 in schemas.py):
   ```python
   class ToolPlan(BaseModel):
       steps: List[ToolCallStep] = ...
   ```
   
   Expects: `{steps: [{tool: "...", params: {...}}, ...]}`

3. **What happens**:
   - LLM generates the list format (following the prompt)
   - LangChain tries to parse it as ToolPlan (following the schema)
   - Format mismatch → parsing fails
   - Line 113 validation fails: `if not isinstance(plan, ToolPlan)`
   - Error is caught and returned as dict
   - Workflow sees error dict and terminates

---

## Affected Code Locations

| File | Lines | Component | Issue |
|------|-------|-----------|-------|
| query_agents.py | 20-28 | System Prompt | Lists bare array expectation |
| query_agents.py | 109-115 | LLM Invocation | No error details captured |
| query_agents.py | 123-130 | Error Handling | Broad exception catching |
| schemas.py | 62-69 | ToolPlan Schema | Defines wrapped structure |
| base_agent.py | 51-60 | Structured Output | Uses with_structured_output() |
| query_workflow.py | 283-296 | Workflow Integration | Calls generate_plan |

---

## Root Cause: Prompt-Schema Mismatch

### The Disconnect

**Prompt** (query_agents.py, lines 21-24):
```
"create a sequential execution plan (a list of JSON objects) to fulfill the query.
...
Output ONLY the JSON list of plan steps, without any other text or explanation."
```

**Schema** (schemas.py, lines 67-69):
```python
class ToolPlan(BaseModel):
    steps: List[ToolCallStep] = Field(
        default_factory=list, 
        description="The sequence of tool calls to execute."
    )
```

The prompt asks for `[{...}, {...}]` but the schema expects `{steps: [{...}, {...}]}`.

---

## Why This Happens

When LangChain's `with_structured_output()` is used:

1. It passes the Pydantic schema to the LLM (telling it the expected format)
2. The system prompt independently tells the LLM to output a bare list
3. These two instructions **conflict**
4. The LLM follows whichever instruction is stronger or clearer
5. If it follows the prompt (bare list), the structured output parser fails
6. If it follows the schema (wrapped object), the prompt validation fails

---

## Impact Analysis

### Severity: HIGH
- **Frequency**: Occurs every time tool-based execution is selected
- **Impact**: Blocks entire tool sequence execution path
- **Recovery**: No fallback mechanism; workflow terminates

### Affected Workflows
1. `execute_query()` node → tool_sequence strategy (lines 278-301)
2. Returns error state instead of execution results
3. Prevents validation and downstream processing

---

## Key Code Flow

```
query_workflow.py:execute_query()
  └─ ToolPlannerAgent.generate_plan(normalized_query, ontology_tools)
      ├─ _get_tool_descriptions(ontology_tools)           [lines 36-56]
      ├─ format system prompt with tools                  [line 69]
      ├─ create user message                              [lines 81-100]
      ├─ _get_structured_llm(ToolPlan)                    [line 109]
      └─ structured_llm.invoke(messages)                  [line 110]
          ├─ LLM called with conflicting instructions
          └─ Returns invalid format
          
      └─ isinstance(plan, ToolPlan) check                 [line 113]
          └─ FAILS - returns dict with error
          
  └─ Error propagation:
      ├─ plan_result.get("error") check                   [line 295]
      ├─ Raises ValueError                                [line 296]
      └─ Caught by outer except block                     [line 361]
          └─ Returns error state
```

---

## Validation Point

Line 113 in query_agents.py is where the validation fails:

```python
if not isinstance(plan, ToolPlan):
    raise ValueError("LLM did not return a list structure as expected for the plan.")
```

This check expects a Pydantic ToolPlan instance, but likely receives:
- A dict (if LLM returned bare list)
- None (if parsing completely failed)
- An exception (if structured output failed)

---

## Secondary Issues

1. **Error Logging** (lines 123-130):
   - Exception is caught broadly
   - Original error details are lost
   - No logging of what LLM actually returned
   - No fallback parsing attempt

2. **Error Handling** (query_workflow.py:296):
   - Error dict triggers ValueError
   - Workflow expects Union[ToolPlan, Dict], but dict case is error
   - Design assumption broken

3. **Tool Filtering** (line 45):
   - Excludes: `["__init__", "execute_sparql", "get_class_richness_info"]`
   - Limits what tools planner can use

---

## Configuration Context

- **LLM Model**: Qwen (qwen-max) from `configs/ace_config.yaml`
- **Structured Output Method**: `model.with_structured_output(ToolPlan)`
- **Provider**: LangChain's structured output with Qwen backend

Qwen should support structured output, so the issue is the prompt-schema conflict, not LLM capability.

---

## Examples

### What Prompt Expects (Bare List)
```json
[
    {"tool": "get_class_info", "params": {"class_name": "compound"}},
    {"tool": "search_classes", "params": {"query": "molecular_weight"}}
]
```

### What Schema Expects (Wrapped)
```json
{
    "steps": [
        {"tool": "get_class_info", "params": {"class_name": "compound"}},
        {"tool": "search_classes", "params": {"query": "molecular_weight"}}
    ]
}
```

### What ToolPlan Object Should Look Like
```python
ToolPlan(
    steps=[
        ToolCallStep(tool="get_class_info", params={"class_name": "compound"}),
        ToolCallStep(tool="search_classes", params={"query": "molecular_weight"})
    ]
)
```

---

## Error Message Flow

1. **Line 115** - Initial error:
   ```python
   raise ValueError("LLM did not return a list structure as expected for the plan.")
   ```

2. **Line 125** - Wrapped error:
   ```python
   error_msg = f"Failed to generate or parse structured tool plan: {str(e)}"
   ```

3. **Line 130** - Returned to workflow:
   ```python
   return {"error": error_msg}
   ```

4. **query_workflow.py:296** - Propagated error:
   ```python
   raise ValueError(f"Failed to generate tool plan: {plan_result.get('error')}")
   ```

5. **query_workflow.py:362** - Final error state:
   ```python
   error_message = f"Query execution failed: {str(e)}"
   return {..., "stage": "error", "error": error_message}
   ```

---

## Investigation Checklist

- [x] Identified error source
- [x] Located schema definition
- [x] Found prompt template
- [x] Mapped error handling
- [x] Traced call stack
- [x] Documented root cause
- [x] Created code snippets
- [x] Analyzed impact
- [ ] (Future) Implement fix
- [ ] (Future) Test solution
- [ ] (Future) Verify with Qwen

---

## Next Steps for Fixing

1. **Option 1: Update Prompt**
   - Change prompt to instruct wrapping in `{steps: [...]}`
   - Align with ToolPlan schema expectation
   - Risk: May reduce LLM's natural output quality

2. **Option 2: Update Schema**
   - Change ToolPlan to accept bare list
   - Create wrapper schema that handles both formats
   - Risk: Changes contract with workflow

3. **Option 3: Add Fallback Parsing**
   - Try to parse both formats
   - Auto-wrap bare lists in ToolPlan
   - Most robust but adds complexity

4. **Option 4: Improve Error Handling**
   - Capture raw LLM output
   - Log detailed error for debugging
   - Add retry with different prompt
   - Recommended as interim solution

---

## Files Containing Analysis

- `/home/syk/projects/experiment-plan-design/TOOL_PLAN_ANALYSIS.md` - Full 13-section analysis
- `/home/syk/projects/experiment-plan-design/TOOL_PLAN_CODE_SNIPPETS.md` - Code excerpts
- `/home/syk/projects/experiment-plan-design/TOOL_PLAN_FAILURE_SUMMARY.md` - This file
- Source code in `/home/syk/projects/experiment-plan-design/src/external/MOSES/autology_constructor/idea/query_team/`

---

## Key Statistics

| Metric | Value |
|--------|-------|
| Error Triggers | query_agents.py:115 |
| Error Caught At | query_agents.py:123 |
| Error Message From | query_agents.py:125 |
| Schema Definition | schemas.py:67-69 |
| Prompt Location | query_agents.py:20-28 |
| Workflow Integration | query_workflow.py:283-296 |
| Error Handling | query_workflow.py:361-370 |
| Total Affected Lines | ~200 lines across 4 files |

---

## Document History

- **Created**: 2024-10-24
- **Status**: COMPLETE - Analysis phase
- **Next Phase**: Fix implementation
- **Reviewed Files**: 
  - query_agents.py (1670 lines)
  - schemas.py (162 lines)
  - base_agent.py (65 lines)
  - query_workflow.py (500+ lines)

