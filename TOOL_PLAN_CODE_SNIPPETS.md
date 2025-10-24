# MOSES Tool Plan Generation - Code Snippets

## 1. Error Location and Stack Trace

### Primary Error (query_agents.py:125)
```python
File: /home/syk/projects/experiment-plan-design/src/external/MOSES/autology_constructor/idea/query_team/query_agents.py

Lines 107-130:
    try:
        # Use the helper method to get the structured LLM
        structured_llm = self._get_structured_llm(ToolPlan)  # Line 109
        plan: ToolPlan = structured_llm.invoke(messages)     # Line 110

        # Basic validation: check if it's a list (LangChain should handle Pydantic validation)
        if not isinstance(plan, ToolPlan):                   # Line 113
            # This case might indicate an issue with the LLM or LangChain's parsing
            raise ValueError("LLM did not return a list structure as expected for the plan.")  # Line 115

        # NEW: 验证和自动修正toolcall参数中的类名
        if isinstance(normalized_query, NormalizedQuery) and normalized_query.relevant_entities:
            plan = self._validate_and_fix_plan_entities(plan, normalized_query.relevant_entities)

        return plan # Return the validated and corrected plan

    except Exception as e:
        # Catch errors during structured output generation/parsing or validation
        error_msg = f"Failed to generate or parse structured tool plan: {str(e)}"  # Line 125
        print(f"{error_msg}") # Log the error
        # Consider logging the raw response if available and helpful for debugging
        # raw_response = getattr(e, 'response', None) # Example, actual attribute might differ
        # print(f"Raw LLM response (if available): {raw_response}")
        return {"error": error_msg} # Return error dictionary  # Line 130
```

---

## 2. ToolPlan Schema Definition

### File: schemas.py (Lines 62-69)
```python
class ToolCallStep(BaseModel):
    """Represents a single step in a tool execution plan."""
    tool: str = Field(
        description="The name of the tool to be called. Must be one of the available OntologyTools methods."
    )
    params: Dict[str, Any] = Field(
        default_factory=dict, 
        description="A dictionary of parameters required to call the specified tool."
    )


class ToolPlan(BaseModel):
    """Represents the planned sequence of tool calls."""
    steps: List[ToolCallStep] = Field(
        default_factory=list, 
        description="The sequence of tool calls to execute."
    )
```

---

## 3. ToolPlannerAgent Class Structure

### File: query_agents.py (Lines 17-193)

#### Class Initialization (Lines 19-34)
```python
class ToolPlannerAgent(AgentTemplate):
    """Generates a tool execution plan based on a normalized query using an LLM."""
    
    def __init__(self, model: BaseLanguageModel):
        system_prompt = """You are an expert planner for ontology tool execution.
Given a normalized query description and a list of available tools with their descriptions, create a sequential execution plan (a list of JSON objects) to fulfill the query.
Each step in the plan should be a JSON object with 'tool' (the tool name) and 'params' (a dictionary of parameters for the tool).
Only use the provided tools. Ensure the parameters match the tool's requirements based on its description.
Output ONLY the JSON list of plan steps, without any other text or explanation.

Available tools:
{tool_descriptions}
"""
        super().__init__(
            model=model,
            name="ToolPlannerAgent",
            system_prompt=system_prompt,
            tools=[] # This agent plans, it doesn't execute tools directly
        )
```

#### Tool Description Generation (Lines 36-56)
```python
def _get_tool_descriptions(self, tool_instance: OntologyTools) -> str:
    """Generates formatted descriptions of OntologyTools methods."""
    descriptions = []
    # Ensure tool_instance is not None
    if tool_instance is None:
        return "No tool instance provided."
        
    for name, method in inspect.getmembers(tool_instance, predicate=inspect.ismethod):
        # Exclude private methods, constructor, and potentially the main execute_sparql if planning should use finer tools
        if not name.startswith("_") and name not in ["__init__", "execute_sparql", "get_class_richness_info"]: 
            try:
                sig = inspect.signature(method)
                doc = inspect.getdoc(method)
                desc = f"- {name}{sig}: {doc if doc else 'No description available.'}"
                descriptions.append(desc)
            except ValueError: # Handles methods without signatures like built-ins if any sneak through
                descriptions.append(f"- {name}(...): No signature/description available.")
    
    # Join descriptions with separator lines for better readability
    separator = "\n" + "-" * 80 + "\n"
    return separator.join(descriptions) if descriptions else "No tools available."
```

#### Main Plan Generation (Lines 58-130)
```python
def generate_plan(self, normalized_query: Union[Dict, NormalizedQuery], ontology_tools: OntologyTools, tool_hints: List = None) -> Union[ToolPlan, Dict]:
    """Generates the tool execution plan with optional tool hints for refinement."""
    if not normalized_query:
         return {"error": "Cannot generate plan from missing normalized query."}
    # Check for error dictionary explicitly
    if isinstance(normalized_query, dict) and normalized_query.get("error"):
         return {"error": f"Cannot generate plan from invalid normalized query: {normalized_query.get('error', 'Unknown error')}"}

    tool_descriptions_str = self._get_tool_descriptions(ontology_tools)
    
    # Prepare prompt using system prompt as template
    formatted_system_prompt = self.system_prompt.format(tool_descriptions=tool_descriptions_str)
    
    # Handle normalized_query being either Dict or Pydantic model for prompt
    try:
        if isinstance(normalized_query, NormalizedQuery):
            normalized_query_str = normalized_query.model_dump_json(indent=2)
        else: # Assume it's a Dict
            normalized_query_str = json.dumps(normalized_query, indent=2, ensure_ascii=False)
    except Exception as dump_error:
         return {"error": f"Failed to serialize normalized query for planning: {dump_error}"}

    # NEW: 构建包含tool hints的用户消息
    user_message = f"""Generate an execution plan for the following normalized query:
{normalized_query_str}

Output the plan as a JSON list of steps matching the ToolCallStep structure."""

    # NEW: 如果有tool hints，添加到用户消息中
    if tool_hints:
        hints_text = []
        for hint in tool_hints:
            hints_text.append(f"- For tool '{hint.tool}' on class '{hint.class_name}': {hint.hint}")
            if hint.alternative_tools:
                hints_text.append(f"  Consider these alternative tools: {', '.join(hint.alternative_tools)}")
        
        hints_section = "\n".join(hints_text)
        user_message += f"""

IMPORTANT REFINEMENT HINTS:
{hints_section}

Please incorporate these hints when generating the tool plan. Use the suggested alternative tools or modifications."""

    messages = [
        ("system", formatted_system_prompt),
        ("user", user_message)
    ]
    
    try:
        # Use the helper method to get the structured LLM
        structured_llm = self._get_structured_llm(ToolPlan)
        plan: ToolPlan = structured_llm.invoke(messages)

        # Basic validation: check if it's a list (LangChain should handle Pydantic validation)
        if not isinstance(plan, ToolPlan):
            # This case might indicate an issue with the LLM or LangChain's parsing
            raise ValueError("LLM did not return a list structure as expected for the plan.")

        # NEW: 验证和自动修正toolcall参数中的类名
        if isinstance(normalized_query, NormalizedQuery) and normalized_query.relevant_entities:
            plan = self._validate_and_fix_plan_entities(plan, normalized_query.relevant_entities)

        return plan # Return the validated and corrected plan

    except Exception as e:
        # Catch errors during structured output generation/parsing or validation
        error_msg = f"Failed to generate or parse structured tool plan: {str(e)}"
        print(f"{error_msg}") # Log the error
        # Consider logging the raw response if available and helpful for debugging
        # raw_response = getattr(e, 'response', None) # Example, actual attribute might differ
        # print(f"Raw LLM response (if available): {raw_response}")
        return {"error": error_msg} # Return error dictionary
```

---

## 4. Structured Output Configuration

### File: base_agent.py (Lines 51-60)
```python
def _get_structured_llm(self, pydantic_schema: Type[T]):
    """Returns an LLM instance configured for structured output with the given Pydantic schema."""
    if not self.model_instance:
        raise ValueError(f"Model instance not available in agent '{self.name}' to configure structured output.")
    try:
        # Use the original model instance for configuring structured output
        return self.model_instance.with_structured_output(pydantic_schema)
    except Exception as e:
        # Handle potential errors during configuration
        raise RuntimeError(f"Failed to configure structured output for schema {pydantic_schema.__name__} in agent '{self.name}': {e}") from e
```

---

## 5. Workflow Integration

### File: query_workflow.py (Lines 278-301)

#### Tool Sequence Execution with Plan Generation
```python
if strategy == "tool_sequence":
    # NEW: 处理来自refiner的tool相关hints
    refiner_hints = state.get("refiner_hints", [])
    tool_related_hints = [h for h in refiner_hints if h.action in ["replace_tool", "replace_both"]]
    
    # 生成执行计划，传递tool hints
    if tool_related_hints:
        print(f"[execute_query] 传递 {len(tool_related_hints)} 个tool hints给planner")
        plan_result = tool_planner_agent.generate_plan(
            normalized_query_obj, 
            ontology_tools, 
            tool_hints=tool_related_hints
        )
    else:
        plan_result = tool_planner_agent.generate_plan(normalized_query_obj, ontology_tools)
    
    # 检查计划生成是否出错
    if isinstance(plan_result, dict) and plan_result.get("error"):
        raise ValueError(f"Failed to generate tool plan: {plan_result.get('error')}")
    elif not isinstance(plan_result, Union[ToolPlan, Dict]):
         raise TypeError(f"Tool planner returned unexpected type: {type(plan_result)}")
    
    # 执行计划
    execution_results = tool_agent.execute_plan(plan_result)
```

#### Error Handling in Workflow (Lines 361-370)
```python
except Exception as e:
    error_message = f"Query execution failed: {str(e)}"
    print(error_message)
    return {
        "status": "error",
        "stage": "error",
        "previous_stage": state.get("stage"),
        "error": error_message,
        "messages": [SystemMessage(content=error_message)]
    }
```

---

## 6. Example Error Propagation

### Complete Error Chain
```
1. ToolPlannerAgent.generate_plan() Line 110
   ↓ LLM returns invalid format
   
2. isinstance(plan, ToolPlan) check fails Line 113
   ↓ Raises ValueError
   
3. Exception caught Line 123
   ↓ error_msg constructed
   
4. Returns {"error": error_msg} Line 130
   ↓ Returned to workflow
   
5. query_workflow.py Line 295
   ↓ Checks if plan_result contains error
   
6. Raises ValueError("Failed to generate tool plan: ...")
   ↓ Caught by outer try-except
   
7. query_workflow.py Line 361
   ↓ Returns error state
   
8. Workflow terminates with stage="error"
```

---

## 7. Input Example

### Normalized Query Structure
```python
NormalizedQuery(
    intent="find information",
    relevant_entities=["compound", "property"],
    relevant_properties=["molecular_weight", "solubility"],
    filters=None,
    query_type_suggestion="fact-finding"
)
```

---

## 8. Expected Output Example

### What Should Be Returned (ToolPlan)
```python
ToolPlan(
    steps=[
        ToolCallStep(
            tool="get_class_info",
            params={"class_name": "compound"}
        ),
        ToolCallStep(
            tool="get_class_properties",
            params={"class_name": "compound", "property_type": "data"}
        ),
        ToolCallStep(
            tool="search_classes",
            params={"query": "molecular_weight"}
        )
    ]
)
```

---

## 9. What LLM Might Return (Problem)

### Bare List Format (Causes Error)
```json
[
    {
        "tool": "get_class_info",
        "params": {
            "class_name": "compound"
        }
    },
    {
        "tool": "get_class_properties",
        "params": {
            "class_name": "compound",
            "property_type": "data"
        }
    }
]
```

**Problem**: This is a list, not a ToolPlan object with a `steps` field.

---

## 10. Import Chain

### File: query_agents.py (Lines 1-15)
```python
from typing import Dict, List, Any, Union, Optional
from autology_constructor.idea.common.base_agent import AgentTemplate
from langchain.prompts import ChatPromptTemplate
from langchain_core.language_models import BaseLanguageModel
import json
import inspect
import re

from .ontology_tools import OntologyTools   
from .utils import parse_json
from config.settings import OntologySettings
from .entity_matcher import EntityMatcher

# Import Pydantic models
from .schemas import (
    NormalizedQuery, ToolCallStep, ValidationReport, DimensionReport, ToolPlan, 
    ExtractedProperties, NormalizedQueryBody, ValidationClassification, 
    ToolCallClassification, GlobalCommunityAssessment, FormattedResult
)
```

