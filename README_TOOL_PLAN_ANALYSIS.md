# MOSES Tool Plan Generation Analysis - README

## Quick Start

You are looking at comprehensive documentation for a specific error in the MOSES query planning subsystem.

**Error**: "Failed to generate or parse structured tool plan: LLM did not return a list structure as expected for the plan."

**Root Cause**: The LLM's system prompt and the ToolPlan Pydantic schema have conflicting format expectations.

---

## Four Analysis Documents

### 1. START HERE: ANALYSIS_INDEX.md (5 min read)
- **Purpose**: Navigation guide and quick reference
- **Best for**: Finding where things are, understanding document structure
- **Contains**: 
  - Document overview
  - Quick navigation table
  - Problem statement with diagram
  - File locations and line numbers
  - Investigation checklist

**Read this first to understand what's available.**

### 2. TOOL_PLAN_FAILURE_SUMMARY.md (5 min read)
- **Purpose**: Executive summary for decision makers
- **Best for**: Understanding the problem and deciding on fixes
- **Contains**:
  - Problem in 30 seconds
  - Root cause explanation
  - Affected code locations table
  - Impact analysis
  - Error message flow
  - 4 possible fix options

**Read this to understand what's wrong and how to fix it.**

### 3. TOOL_PLAN_ANALYSIS.md (15 min read)
- **Purpose**: Comprehensive technical analysis
- **Best for**: Understanding the architecture and implementation details
- **Contains**:
  - 13 detailed sections:
    1. Error source (query_agents.py:125)
    2. ToolPlan schema definition (schemas.py:67-69)
    3. Tool plan generation function (step-by-step)
    4. LLM system prompt (root of problem)
    5. Structured output configuration (base_agent.py:51-60)
    6. Root cause analysis (Primary + Secondary)
    7. Call stack and workflow integration
    8. Expected structure examples
    9. Validation failure analysis
    10. Normal vs error code flows
    11. Issue summary table
    12. Files involved
    13. Configuration context

**Read this for deep understanding of how everything fits together.**

### 4. TOOL_PLAN_CODE_SNIPPETS.md (20 min read)
- **Purpose**: Code reference with full context
- **Best for**: Reviewing actual code, preparing for implementation
- **Contains**:
  - 10 major code sections with full context
  - All relevant line numbers
  - Error location with try-catch
  - Schema definitions
  - Complete class structure
  - Workflow integration code
  - Error handling flow
  - Input/output examples
  - Import chains

**Read this when reviewing or modifying the actual code.**

---

## How to Use These Documents

### Scenario 1: I just heard about this error
1. Read ANALYSIS_INDEX.md (find the problem)
2. Read TOOL_PLAN_FAILURE_SUMMARY.md (understand what it means)
3. Skim TOOL_PLAN_ANALYSIS.md (get the big picture)

### Scenario 2: I need to fix this
1. Read TOOL_PLAN_FAILURE_SUMMARY.md (section: "Next Steps for Fixing")
2. Read TOOL_PLAN_CODE_SNIPPETS.md (review the code)
3. Read TOOL_PLAN_ANALYSIS.md (understand the implications)
4. Implement your chosen fix

### Scenario 3: I need to understand why it fails
1. Read TOOL_PLAN_ANALYSIS.md section 6 (root cause)
2. Read TOOL_PLAN_ANALYSIS.md section 9 (why validation fails)
3. Review code snippets for the specific areas

### Scenario 4: I need to find specific information
1. Use ANALYSIS_INDEX.md Quick Navigation table
2. Jump to the referenced section in the appropriate document

---

## The Problem in 60 Seconds

```
ToolPlannerAgent generates execution plans for ontology queries.

System Prompt tells LLM:
  "Output ONLY the JSON list of plan steps"
  Expected: [{"tool": "...", "params": {...}}, ...]

ToolPlan Schema expects:
  class ToolPlan(BaseModel):
      steps: List[ToolCallStep]
  Expected: {"steps": [{"tool": "...", "params": {...}}, ...]}

When LLM runs:
  It follows the system prompt (bare list)
  LangChain tries to parse as ToolPlan (wrapped structure)
  Parsing fails
  Line 113: isinstance(plan, ToolPlan) returns False
  Line 115: Raises ValueError
  Line 125: Wraps error message
  Line 130: Returns {"error": "..."}

Workflow:
  Sees error dict
  Raises ValueError at line 296
  Caught by outer exception handler
  Returns error state (stage="error")

Result: Tool-based query execution fails completely
```

---

## File Locations

### Analysis Documents
- `/home/syk/projects/experiment-plan-design/ANALYSIS_INDEX.md`
- `/home/syk/projects/experiment-plan-design/TOOL_PLAN_FAILURE_SUMMARY.md`
- `/home/syk/projects/experiment-plan-design/TOOL_PLAN_ANALYSIS.md`
- `/home/syk/projects/experiment-plan-design/TOOL_PLAN_CODE_SNIPPETS.md`
- `/home/syk/projects/experiment-plan-design/README_TOOL_PLAN_ANALYSIS.md` (this file)

### Source Code
- **ToolPlannerAgent**: `src/external/MOSES/autology_constructor/idea/query_team/query_agents.py` (lines 17-193)
- **ToolPlan Schema**: `src/external/MOSES/autology_constructor/idea/query_team/schemas.py` (lines 62-69)
- **Base Agent**: `src/external/MOSES/autology_constructor/idea/common/base_agent.py` (lines 51-60)
- **Workflow**: `src/external/MOSES/autology_constructor/idea/query_team/query_workflow.py` (lines 283-296, 361-370)

---

## Key Line Numbers

| What | File | Line(s) |
|------|------|---------|
| Error trigger | query_agents.py | 115 |
| Error message | query_agents.py | 125 |
| System prompt | query_agents.py | 20-28 |
| LLM invocation | query_agents.py | 109-110 |
| ToolPlan schema | schemas.py | 67-69 |
| ToolCallStep schema | schemas.py | 62-65 |
| Structured output config | base_agent.py | 51-60 |
| Workflow call | query_workflow.py | 286-292 |
| Error check | query_workflow.py | 295 |
| Error handler | query_workflow.py | 361-370 |

---

## Four Fix Options

From TOOL_PLAN_FAILURE_SUMMARY.md:

1. **Option 1: Update Prompt** - Change to match schema
2. **Option 2: Update Schema** - Change to match prompt  
3. **Option 3: Add Fallback Parsing** - Handle both formats
4. **Option 4: Improve Error Handling** - Better diagnostics (recommended interim)

See TOOL_PLAN_FAILURE_SUMMARY.md for details on each approach.

---

## Key Insights

### What Works
- QueryParserAgent (uses structured output successfully)
- ValidationAgent (uses multiple structured LLMs)
- ResultFormatterAgent (uses FormattedResult schema)
- Other agents in the system

### What Doesn't Work
- ToolPlannerAgent tool plan generation
- Prompt-schema mismatch is the culprit
- Tool-sequence execution path is blocked

### Why It's a Problem
- Every tool-based query fails
- No recovery mechanism
- No clear error message to user
- Workflow terminates with error state

---

## Statistics

- **Error Frequency**: Every tool_sequence execution
- **Severity**: HIGH - Complete path blockage
- **Files Affected**: 4 major files
- **Lines Involved**: ~200 lines
- **Code Examined**: ~1800 lines
- **Documentation Generated**: 5 files, 45+ KB
- **Time to Read All**: ~45 minutes
- **Time to Understand Root Cause**: ~10 minutes

---

## What's Next

1. **Review** any one of the documents (start with ANALYSIS_INDEX.md)
2. **Understand** the root cause (read TOOL_PLAN_FAILURE_SUMMARY.md)
3. **Choose** your fix approach (section "Next Steps for Fixing")
4. **Review** the code (use TOOL_PLAN_CODE_SNIPPETS.md)
5. **Implement** your fix
6. **Test** with actual Qwen calls
7. **Verify** end-to-end

---

## Questions?

Each document is self-contained and cross-referenced. Use the Quick Navigation table in ANALYSIS_INDEX.md to find specific information.

---

## Document Version History

- **Created**: 2024-10-24
- **Status**: Complete - Ready for implementation
- **Next Phase**: Fix implementation and testing

---

**Total Content**: 4 detailed analysis documents + this README = Comprehensive coverage of the tool plan generation failure in MOSES.
