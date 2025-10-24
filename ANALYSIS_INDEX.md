# MOSES Tool Plan Generation Failure - Complete Analysis Index

## Overview

Comprehensive analysis of the error: **"Failed to generate or parse structured tool plan: LLM did not return a list structure as expected for the plan."**

**Root Cause**: Mismatch between LLM system prompt (expects bare JSON list) and Pydantic schema (expects wrapped object with `steps` field).

---

## Documents Generated

### 1. Executive Summary
**File**: `TOOL_PLAN_FAILURE_SUMMARY.md`
**Purpose**: Quick reference, 5-minute read
**Contains**:
- Problem in 30 seconds
- Affected code locations
- Root cause explanation
- Key code flow diagram
- Impact analysis
- 4 possible fix options

### 2. Detailed Analysis
**File**: `TOOL_PLAN_ANALYSIS.md`
**Purpose**: Complete technical analysis, 15-minute read
**Contains**:
- 13 major sections covering:
  1. Error source location (exact line numbers)
  2. ToolPlan schema definition
  3. Tool plan generation function (step-by-step)
  4. LLM system prompt
  5. Structured output configuration
  6. Root cause analysis (Primary + Secondary issues)
  7. Call stack where tool plan is used
  8. Expected list structure (with examples)
  9. Why validation fails
  10. Normal vs error code flows
  11. Summary table of all issues
  12. Files involved
  13. Configuration context

### 3. Code Snippets
**File**: `TOOL_PLAN_CODE_SNIPPETS.md`
**Purpose**: Reference material, 20-minute read
**Contains**:
- 10 major code sections:
  1. Error location with exact lines
  2. ToolPlan schema definition
  3. ToolPlannerAgent class structure
  4. Structured output configuration
  5. Workflow integration
  6. Error handling in workflow
  7. Error propagation chain
  8. Input example
  9. Expected output example
  10. What LLM might return (problematic)
  11. Import chain
  
All with line numbers and full context

---

## Quick Navigation

### Finding Specific Information

| Question | Document | Section |
|----------|----------|---------|
| What's the root cause? | SUMMARY | "Root Cause: Prompt-Schema Mismatch" |
| Where does the error occur? | ANALYSIS | "1. Error Source Location" |
| Show me the schema | SNIPPETS | "2. ToolPlan Schema Definition" |
| What's the system prompt? | ANALYSIS | "4. LLM System Prompt" |
| How does the workflow work? | ANALYSIS | "7. Call Stack" or SNIPPETS | "5. Workflow Integration" |
| What should be returned? | ANALYSIS | "8. Expected List Structure" |
| Why does validation fail? | ANALYSIS | "9. Why the Validation Fails" |
| Show the error flow | SNIPPETS | "6. Error Propagation Chain" |
| What are my fix options? | SUMMARY | "Next Steps for Fixing" |

### By File Location

**query_agents.py** - ToolPlannerAgent class
- Lines 17-193: Full class definition
- Lines 20-28: System prompt (root of problem)
- Lines 36-56: Tool description generation
- Lines 58-130: Main generate_plan method
- Line 109: LLM invocation
- Line 115: Error trigger
- Line 125: Error message

**schemas.py** - Data models
- Lines 62-69: ToolCallStep and ToolPlan classes (schema definition)

**base_agent.py** - Base agent template
- Lines 51-60: _get_structured_llm method

**query_workflow.py** - Workflow graph
- Lines 283-296: Tool plan generation call in execute_query node
- Lines 361-370: Error handling

---

## Problem Statement

### The Core Issue

```
Prompt says:                    Schema says:                  Result:
"Output ONLY the JSON           {                             Conflict!
 list of plan steps"            "steps": [...]                ↓
                                }                             Parse error
Input:  [...]                   Input: {...}                  ↓
Output: [...]                   Output: {steps: [...]}        Not isinstance(plan, ToolPlan)
                                                               ↓
                                                               Error returned
```

---

## Key Findings

### Primary Issue: Prompt-Schema Mismatch
- **Location**: query_agents.py (system prompt) vs schemas.py (ToolPlan class)
- **Type**: Structural conflict between expected output formats
- **Severity**: HIGH - Blocks tool-based query execution entirely

### Secondary Issues
1. **Error Logging**: Loses original error details (line 123)
2. **Error Handling**: No fallback parsing (line 107-130)
3. **Tool Filtering**: Excludes some available tools (line 45)

### Impact
- Frequency: Every tool_sequence strategy execution
- Scope: Full tool plan generation + execution
- Recovery: None - workflow terminates with error state

---

## Expected vs Actual

### Expected Behavior
```python
# LLM generates
ToolPlan(
    steps=[
        ToolCallStep(tool="get_class_info", params={"class_name": "compound"})
    ]
)

# Workflow receives
ToolPlan instance (isinstance check passes)

# Workflow executes
execute_plan(plan_result) → execution results → validation → success
```

### Actual Behavior
```python
# LLM generates (following prompt)
[
    {"tool": "get_class_info", "params": {"class_name": "compound"}}
]

# LangChain tries to parse as ToolPlan
# Parsing fails - doesn't match schema

# Workflow receives
dict with error: "Failed to generate or parse structured tool plan: ..."

# Workflow executes
raise ValueError → error state → workflow terminates
```

---

## Code Trace

### Normal Execution Path (If Fixed)
```
normalize_query()
  ↓ Returns NormalizedQuery
determine_strategy()
  ↓ Returns "tool_sequence"
execute_query()
  ├─ ToolPlannerAgent.generate_plan()        [Should return ToolPlan]
  ├─ _get_structured_llm(ToolPlan)
  ├─ structured_llm.invoke(messages)         [LLM call]
  ├─ isinstance(plan, ToolPlan) ✓
  ├─ ToolExecutorAgent.execute_plan()        [Plan execution]
  └─ Returns execution_results
validate_results()
  └─ Returns validation_report
```

### Error Execution Path (Current State)
```
execute_query()
  ├─ ToolPlannerAgent.generate_plan()        [Line 286/292]
  ├─ _get_structured_llm(ToolPlan)           [Line 109]
  ├─ structured_llm.invoke(messages)         [Line 110]
  │   └─ LLM returns bare list format
  ├─ isinstance(plan, ToolPlan) ✗            [Line 113]
  ├─ raise ValueError()                      [Line 115]
  ├─ Exception caught                        [Line 123]
  ├─ error_msg constructed                   [Line 125]
  └─ return {"error": error_msg}             [Line 130]
    ↓
  Plan result check                          [Line 295]
  ├─ if isinstance(plan_result, dict) and .get("error")
  ├─ raise ValueError()                      [Line 296]
  └─ Caught by outer except                  [Line 361]
    ↓
  Return error state
  └─ stage = "error"
```

---

## Metrics

| Metric | Value |
|--------|-------|
| Primary Error Line | query_agents.py:115 |
| Error Wrapped At | query_agents.py:125 |
| Schema Definition | schemas.py:67-69 |
| Prompt Location | query_agents.py:20-28 |
| Workflow Call | query_workflow.py:286-292 |
| Error Detection | query_workflow.py:295 |
| Final Handler | query_workflow.py:361 |
| Files Affected | 4 major files |
| Total Code Lines | ~200 lines affected |
| Blocks | tool_sequence strategy path |
| Impact Frequency | Every tool-based query |

---

## Related Code

### Similar Agents (For Reference)
- **QueryParserAgent**: Also uses structured output successfully
- **ValidationAgent**: Uses multiple structured LLMs
- **ResultFormatterAgent**: Uses FormattedResult schema

These agents appear to work correctly, suggesting the issue is specific to ToolPlannerAgent's prompt-schema mismatch.

---

## Configuration Details

From project configuration:
- **LLM**: Qwen (qwen-max)
- **Config File**: `configs/ace_config.yaml`
- **Structured Output Method**: `model.with_structured_output(ToolPlan)`
- **Provider**: LangChain with Qwen backend
- **Embedding Model**: BAAI/bge-large-zh-v1.5

Qwen supports structured output, so issue is not capability-based.

---

## Investigation Completeness

### Completed
- [x] Error source location identified
- [x] Schema definition located and analyzed
- [x] Prompt template found and reviewed
- [x] Error message generation traced
- [x] Workflow integration mapped
- [x] Call stack reconstructed
- [x] Root cause identified
- [x] Code examples created
- [x] Impact analysis completed
- [x] Fix options outlined

### Ready For
- [ ] Implementation
- [ ] Testing
- [ ] Verification with Qwen
- [ ] Deployment

---

## How to Use These Documents

1. **First Time Reading**: Start with SUMMARY
2. **Understanding Root Cause**: Read ANALYSIS section 6
3. **Detailed Code Review**: Use SNIPPETS with original files
4. **Finding Specific Issues**: Use Quick Navigation table
5. **Planning Fixes**: Review SUMMARY "Next Steps for Fixing"

---

## File Locations

All analysis documents in project root:
- `/home/syk/projects/experiment-plan-design/TOOL_PLAN_FAILURE_SUMMARY.md`
- `/home/syk/projects/experiment-plan-design/TOOL_PLAN_ANALYSIS.md`
- `/home/syk/projects/experiment-plan-design/TOOL_PLAN_CODE_SNIPPETS.md`
- `/home/syk/projects/experiment-plan-design/ANALYSIS_INDEX.md` (this file)

Source code:
- `/home/syk/projects/experiment-plan-design/src/external/MOSES/autology_constructor/idea/query_team/query_agents.py`
- `/home/syk/projects/experiment-plan-design/src/external/MOSES/autology_constructor/idea/query_team/schemas.py`
- `/home/syk/projects/experiment-plan-design/src/external/MOSES/autology_constructor/idea/query_team/query_workflow.py`
- `/home/syk/projects/experiment-plan-design/src/external/MOSES/autology_constructor/idea/common/base_agent.py`

---

## Next Actions

1. **Review** all three analysis documents
2. **Choose** one of the 4 fix options from SUMMARY
3. **Implement** the chosen solution
4. **Test** with actual Qwen LLM calls
5. **Verify** fix works end-to-end

---

## Document Information

- **Analysis Date**: 2024-10-24
- **Status**: Complete
- **Scope**: MOSES query_team tool planning subsystem
- **Depth**: Comprehensive (13 sections, 10 code sections)
- **Line Coverage**: ~1800 lines of code examined
- **Files Analyzed**: 4 major files
- **Generated Documentation**: 4 markdown files

