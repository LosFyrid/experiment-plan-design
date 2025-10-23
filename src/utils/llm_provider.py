"""
LLM Provider for ACE Framework.

Provides unified interface for LLM API calls (Qwen, OpenAI, etc.).
"""

import os
from typing import List, Dict, Optional, Any, Union
from dataclasses import dataclass
import json


@dataclass
class LLMResponse:
    """Standardized LLM response format."""
    content: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    finish_reason: Optional[str] = None
    raw_response: Optional[Any] = None


class BaseLLMProvider:
    """Base class for LLM providers."""

    def __init__(
        self,
        model_name: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ):
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.extra_params = kwargs

    def chat(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> LLMResponse:
        """
        Send chat completion request.

        Args:
            messages: List of message dicts with 'role' and 'content'
            **kwargs: Additional parameters

        Returns:
            LLMResponse
        """
        raise NotImplementedError

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate text from a single prompt.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            **kwargs: Additional parameters

        Returns:
            LLMResponse
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        return self.chat(messages, **kwargs)


class QwenProvider(BaseLLMProvider):
    """
    Qwen LLM provider using DashScope API.

    Requires DASHSCOPE_API_KEY environment variable.
    """

    def __init__(
        self,
        model_name: str = "qwen-max",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ):
        super().__init__(model_name, temperature, max_tokens, **kwargs)

        # Import DashScope (lazy import to avoid dependency issues)
        try:
            import dashscope
            from dashscope import Generation
            self.dashscope = dashscope
            self.Generation = Generation
        except ImportError:
            raise ImportError(
                "dashscope package not found. Install with: pip install dashscope"
            )

        # Set API key
        api_key = os.getenv("DASHSCOPE_API_KEY")
        if not api_key:
            raise ValueError("DASHSCOPE_API_KEY environment variable not set")

        self.dashscope.api_key = api_key

    def chat(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> LLMResponse:
        """
        Send chat completion request to Qwen.

        Args:
            messages: List of message dicts with 'role' and 'content'
            **kwargs: Additional parameters (overrides defaults)

        Returns:
            LLMResponse
        """
        # Merge parameters
        params = {
            "model": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            **self.extra_params,
            **kwargs
        }

        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}

        # Make API call
        response = self.Generation.call(
            messages=messages,
            result_format='message',  # Use message format for structured output
            **params
        )

        # Check for errors
        if response.status_code != 200:
            error_msg = f"Qwen API error: {response.code} - {response.message}"
            raise RuntimeError(error_msg)

        # Extract content
        output = response.output
        content = output.choices[0].message.content

        # Extract token usage
        usage = response.usage
        prompt_tokens = usage.input_tokens
        completion_tokens = usage.output_tokens
        total_tokens = usage.total_tokens

        return LLMResponse(
            content=content,
            model=self.model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            finish_reason=output.choices[0].finish_reason,
            raw_response=response
        )


class OpenAIProvider(BaseLLMProvider):
    """
    OpenAI LLM provider.

    Requires OPENAI_API_KEY environment variable.
    """

    def __init__(
        self,
        model_name: str = "gpt-4",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ):
        super().__init__(model_name, temperature, max_tokens, **kwargs)

        # Import OpenAI (lazy import)
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        except ImportError:
            raise ImportError(
                "openai package not found. Install with: pip install openai"
            )

    def chat(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> LLMResponse:
        """
        Send chat completion request to OpenAI.

        Args:
            messages: List of message dicts with 'role' and 'content'
            **kwargs: Additional parameters

        Returns:
            LLMResponse
        """
        # Merge parameters
        params = {
            "model": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            **self.extra_params,
            **kwargs
        }

        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}

        # Make API call
        response = self.client.chat.completions.create(
            messages=messages,
            **params
        )

        # Extract content
        content = response.choices[0].message.content
        finish_reason = response.choices[0].finish_reason

        # Extract token usage
        usage = response.usage
        prompt_tokens = usage.prompt_tokens
        completion_tokens = usage.completion_tokens
        total_tokens = usage.total_tokens

        return LLMResponse(
            content=content,
            model=self.model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            finish_reason=finish_reason,
            raw_response=response
        )


# ============================================================================
# Provider Factory
# ============================================================================

def create_llm_provider(
    provider: str = "qwen",
    model_name: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    **kwargs
) -> BaseLLMProvider:
    """
    Factory function to create LLM provider.

    Args:
        provider: "qwen" or "openai"
        model_name: Model name (uses default if None)
        temperature: Sampling temperature
        max_tokens: Maximum tokens to generate
        **kwargs: Additional provider-specific parameters

    Returns:
        BaseLLMProvider instance

    Raises:
        ValueError: If provider is not supported
    """
    provider = provider.lower()

    if provider == "qwen":
        if model_name is None:
            model_name = os.getenv("DEFAULT_LLM_MODEL", "qwen-max")
        return QwenProvider(model_name, temperature, max_tokens, **kwargs)

    elif provider == "openai":
        if model_name is None:
            model_name = "gpt-4"
        return OpenAIProvider(model_name, temperature, max_tokens, **kwargs)

    else:
        raise ValueError(f"Unsupported provider: {provider}")


# ============================================================================
# Convenience Functions
# ============================================================================

def get_default_provider() -> BaseLLMProvider:
    """
    Get default LLM provider from environment settings.

    Returns:
        BaseLLMProvider instance
    """
    from .config_loader import get_ace_config

    config = get_ace_config()
    return create_llm_provider(
        provider=config.model.provider,
        model_name=config.model.model_name,
        temperature=config.model.temperature,
        max_tokens=config.model.max_tokens
    )


def parse_json_response(response: LLMResponse) -> Dict:
    """
    Parse JSON from LLM response.

    Handles markdown code blocks and direct JSON.

    Args:
        response: LLMResponse instance

    Returns:
        Parsed JSON dict

    Raises:
        ValueError: If JSON parsing fails
    """
    content = response.content.strip()

    # Remove markdown code blocks if present
    if content.startswith("```json"):
        content = content[7:]  # Remove ```json
    elif content.startswith("```"):
        content = content[3:]  # Remove ```

    if content.endswith("```"):
        content = content[:-3]  # Remove trailing ```

    content = content.strip()

    # Parse JSON
    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON from LLM response: {e}\nContent: {content}")


def extract_json_from_text(text: str) -> Optional[Dict]:
    """
    Extract JSON object from mixed text (with explanations before/after).

    Args:
        text: Text that may contain JSON

    Returns:
        Parsed JSON dict or None if not found
    """
    import re

    # Try to find JSON object pattern
    json_pattern = r'\{(?:[^{}]|(?:\{(?:[^{}]|(?:\{[^{}]*\})*)*\})*)*\}'

    matches = re.findall(json_pattern, text, re.DOTALL)

    for match in reversed(matches):  # Try from end (likely to be actual output)
        try:
            return json.loads(match)
        except json.JSONDecodeError:
            continue

    return None
