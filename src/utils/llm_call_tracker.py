"""
LLM Call Tracker (A4) - Track all LLM API calls for debugging and replay.

Provides:
- Complete request/response logging
- Prompt and response saving
- Token usage tracking
- Call replay capability
- Performance metrics per call
"""

import json
import time
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

from .logs_manager import LogsManager, get_logs_manager


class LLMCallTracker:
    """
    Track all LLM API calls with complete context.

    Features:
    - Save complete request (system_prompt + user_prompt)
    - Save complete response
    - Track timing and tokens
    - Enable replay for debugging
    - Support A/B testing of prompts
    """

    def __init__(
        self,
        component: str,
        run_id: Optional[str] = None,
        logs_manager: Optional[LogsManager] = None
    ):
        """
        Args:
            component: Component name (generator/reflector/curator)
            run_id: Run ID to associate with (uses current if None)
            logs_manager: LogsManager instance (uses default if None)
        """
        self.component = component
        self.logs_manager = logs_manager or get_logs_manager()
        self.run_id = run_id or self.logs_manager.current_run_id

        # Current call context
        self.current_call_id: Optional[str] = None
        self.current_call_start: Optional[float] = None

    # ========================================================================
    # Call Tracking
    # ========================================================================

    def start_call(
        self,
        model_provider: str,
        model_name: str,
        config: Dict[str, Any],
        system_prompt: str,
        user_prompt: str,
        stage: str = "",
        detail: str = ""
    ) -> str:
        """
        Start tracking an LLM call.

        Args:
            model_provider: Provider name (e.g., "qwen", "openai")
            model_name: Model name (e.g., "qwen-max")
            config: Model config (temperature, max_tokens, etc.)
            system_prompt: System prompt content
            user_prompt: User prompt content
            stage: Stage name (e.g., "generation", "reflection")
            detail: Additional detail (e.g., "round1", "round2")

        Returns:
            Call ID for later reference
        """
        # Generate call ID
        timestamp = datetime.now().strftime("%H%M%S")
        run_id = self.run_id or "unknown"

        if detail:
            call_id = f"{timestamp}_{run_id}_{self.component}_{detail}"
        else:
            call_id = f"{timestamp}_{run_id}_{self.component}"

        self.current_call_id = call_id
        self.current_call_start = time.time()

        # Save call metadata immediately (will update with response later)
        call_data = {
            "llm_call_id": call_id,
            "run_id": self.run_id,
            "timestamp": datetime.now().isoformat(),
            "component": self.component,
            "stage": stage,
            "model": {
                "provider": model_provider,
                "name": model_name,
                "config": config
            },
            "request": {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "prompt_length": len(user_prompt)
            },
            "response": None,  # Will be filled in end_call
            "tokens": None,
            "timing": {
                "started_at": datetime.now().isoformat(),
                "completed_at": None,
                "duration": None
            },
            "status": "in_progress"
        }

        # Get file path
        file_path = self.logs_manager.get_llm_call_path(
            component=self.component,
            detail=detail,
            run_id=self.run_id
        )

        # Save to file
        with open(file_path, "w") as f:
            json.dump(call_data, f, indent=2)

        return call_id

    def end_call(
        self,
        response: str,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        status: str = "success",
        error: Optional[str] = None
    ):
        """
        Complete an LLM call tracking.

        Args:
            response: LLM response content
            input_tokens: Number of input tokens (if available)
            output_tokens: Number of output tokens (if available)
            status: Call status ("success", "error")
            error: Error message if status is "error"
        """
        if not self.current_call_id or not self.current_call_start:
            print("Warning: end_call called without start_call")
            return

        duration = time.time() - self.current_call_start

        # Find the call file
        call_files = list(self.logs_manager.llm_calls_dir.glob(f"**/{self.current_call_id}.json"))

        if not call_files:
            print(f"Warning: Call file not found for {self.current_call_id}")
            return

        call_file = call_files[0]

        # Load existing data
        with open(call_file, "r") as f:
            call_data = json.load(f)

        # Update with response data
        call_data["response"] = {
            "content": response,
            "length": len(response)
        }

        if input_tokens is not None and output_tokens is not None:
            call_data["tokens"] = {
                "input": input_tokens,
                "output": output_tokens,
                "total": input_tokens + output_tokens
            }

        call_data["timing"]["completed_at"] = datetime.now().isoformat()
        call_data["timing"]["duration"] = duration
        call_data["status"] = status

        if error:
            call_data["error"] = error

        # Save updated data
        with open(call_file, "w") as f:
            json.dump(call_data, f, indent=2)

        # Reset current call context
        self.current_call_id = None
        self.current_call_start = None

    # ========================================================================
    # Simplified API
    # ========================================================================

    def track_call(
        self,
        model_provider: str,
        model_name: str,
        config: Dict[str, Any],
        system_prompt: str,
        user_prompt: str,
        response: str,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        stage: str = "",
        detail: str = "",
        status: str = "success",
        error: Optional[str] = None
    ) -> str:
        """
        Track a complete LLM call (start + end in one call).

        Useful when you have all data available at once.

        Args:
            (same as start_call + end_call)

        Returns:
            Call ID
        """
        call_id = self.start_call(
            model_provider=model_provider,
            model_name=model_name,
            config=config,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            stage=stage,
            detail=detail
        )

        # Simulate duration for synchronous calls
        # (start time was already set in start_call)
        time.sleep(0.001)  # Minimal delay to show it's not instant

        self.end_call(
            response=response,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            status=status,
            error=error
        )

        return call_id

    # ========================================================================
    # Query and Replay
    # ========================================================================

    def get_call_data(self, call_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve data for a specific call.

        Args:
            call_id: Call ID to retrieve

        Returns:
            Call data dictionary or None if not found
        """
        call_files = list(self.logs_manager.llm_calls_dir.glob(f"**/{call_id}.json"))

        if call_files:
            with open(call_files[0], "r") as f:
                return json.load(f)

        return None

    def list_calls(
        self,
        component: Optional[str] = None,
        run_id: Optional[str] = None,
        status: Optional[str] = None
    ) -> list[Dict[str, Any]]:
        """
        List all tracked calls, optionally filtered.

        Args:
            component: Filter by component
            run_id: Filter by run ID
            status: Filter by status

        Returns:
            List of call data dictionaries
        """
        calls = []

        for call_file in self.logs_manager.llm_calls_dir.glob("**/*.json"):
            with open(call_file, "r") as f:
                call_data = json.load(f)

            # Apply filters
            if component and call_data.get("component") != component:
                continue
            if run_id and call_data.get("run_id") != run_id:
                continue
            if status and call_data.get("status") != status:
                continue

            calls.append(call_data)

        return calls

    def export_prompt(self, call_id: str, output_path: str):
        """
        Export just the prompt from a call to a text file.

        Useful for manual inspection and editing.

        Args:
            call_id: Call ID
            output_path: Path to save prompt
        """
        call_data = self.get_call_data(call_id)

        if not call_data:
            raise ValueError(f"Call not found: {call_id}")

        request = call_data.get("request", {})
        system_prompt = request.get("system_prompt", "")
        user_prompt = request.get("user_prompt", "")

        with open(output_path, "w") as f:
            f.write("=" * 60 + "\n")
            f.write("SYSTEM PROMPT\n")
            f.write("=" * 60 + "\n\n")
            f.write(system_prompt)
            f.write("\n\n")
            f.write("=" * 60 + "\n")
            f.write("USER PROMPT\n")
            f.write("=" * 60 + "\n\n")
            f.write(user_prompt)

    # ========================================================================
    # Analysis
    # ========================================================================

    def get_token_stats(
        self,
        component: Optional[str] = None,
        run_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get token usage statistics.

        Args:
            component: Optional component filter
            run_id: Optional run ID filter

        Returns:
            Token statistics dictionary
        """
        calls = self.list_calls(component=component, run_id=run_id, status="success")

        if not calls:
            return {
                "total_calls": 0,
                "total_tokens": 0,
                "total_input": 0,
                "total_output": 0
            }

        total_input = 0
        total_output = 0
        calls_with_tokens = 0

        for call in calls:
            tokens = call.get("tokens")
            if tokens:
                total_input += tokens.get("input", 0)
                total_output += tokens.get("output", 0)
                calls_with_tokens += 1

        return {
            "total_calls": len(calls),
            "calls_with_tokens": calls_with_tokens,
            "total_tokens": total_input + total_output,
            "total_input": total_input,
            "total_output": total_output,
            "avg_input": total_input / calls_with_tokens if calls_with_tokens > 0 else 0,
            "avg_output": total_output / calls_with_tokens if calls_with_tokens > 0 else 0
        }

    def get_slowest_calls(self, top_n: int = 5) -> list[Dict[str, Any]]:
        """
        Get the slowest LLM calls.

        Args:
            top_n: Number of top calls to return

        Returns:
            List of call data sorted by duration
        """
        calls = self.list_calls(status="success")

        # Filter calls with timing data and sort by duration
        calls_with_timing = [
            call for call in calls
            if call.get("timing", {}).get("duration") is not None
        ]

        calls_with_timing.sort(
            key=lambda c: c["timing"]["duration"],
            reverse=True
        )

        return calls_with_timing[:top_n]


# Factory function
def create_llm_call_tracker(
    component: str,
    run_id: Optional[str] = None,
    logs_manager: Optional[LogsManager] = None
) -> LLMCallTracker:
    """Create an LLMCallTracker instance."""
    return LLMCallTracker(component, run_id, logs_manager)
