"""LLM client (OpenAI protocol) + MockLLMClient for testing.

Supports MiniMax M3 (api.minimaxi.com/v1) and StepFun step-3.7-flash
(api.stepfun.com/step_plan/v1). Both use OpenAI-compatible chat completions.

Configured via env vars:
- MINIMAX_API_KEY: API key (shared name for backwards compat)
- LLM_BASE_URL: endpoint (default: StepFun step_plan)
- LLM_MODEL: model name (default: step-3.7-flash)

Both MiniMax and StepFun are reasoning models — they emit thinking before
the actual content. MiniMax wraps it in <think>...</think> inside content;
StepFun puts it in a separate `reasoning` field. extractContent() handles both.

This module provides:
- MiniMaxClient: real client using openai SDK (name kept for backwards compat)
- MockLLMClient: for tests, accepts preset responses
- extractContent: strips <think>...</think> from content (MiniMax only;
  StepFun content is already clean)
"""

import os
import re

from openai import AsyncOpenAI


def extractContent(text: str) -> str:
    """Strip <think>...</think> reasoning blocks from LLM output.

    Both MiniMax-M2.1 and MiniMax-M3 wrap their thinking in <think>...</think>
    before the actual content. JSON parsers will fail if thinking contains
    stray { or } characters. Call this on the raw response before parsing.

    Args:
        text: Raw assistant message content from OpenAI chat.completions.

    Returns:
        Cleaned text with thinking blocks removed and whitespace stripped.
    """
    if not text:
        return ""
    # Match <think>...</think> (non-greedy, multiline)
    cleaned = re.sub(r"<think>.*?</think>\s*", "", text, flags=re.DOTALL)
    return cleaned.strip()


class MiniMaxClient:
    """OpenAI-protocol LLM client. Supports MiniMax M3 + StepFun step-3.7-flash.

    Configured via env vars:
    - MINIMAX_API_KEY: API key (shared name for backwards compat)
    - LLM_BASE_URL: endpoint (default: StepFun)
    - LLM_MODEL: model name (default: step-3.7-flash)
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = os.environ.get("LLM_BASE_URL", "https://api.stepfun.com/step_plan/v1"),
        model: str = os.environ.get("LLM_MODEL", "step-3.7-flash"),
    ):
        self.client = AsyncOpenAI(
            api_key=api_key or os.environ["MINIMAX_API_KEY"],
            base_url=base_url,
        )
        self.model = model

    async def chat(self, prompt: str, max_tokens: int = 2000) -> str:
        """Call MiniMax M3 chat completion. Returns the assistant content.

        Returns raw content (may contain <think>...</think> blocks).
        Use `extractContent()` to strip reasoning before JSON parsing.

        Raises on network errors or non-2xx responses (caller handles).
        """
        r = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
        )
        return r.choices[0].message.content or ""


class MockLLMClient:
    """Mock client for tests. Accepts a single response string or list of
    per-call responses (for per-card isolation tests).

    Example:
        mock = MockLLMClient(response='{"tags": ["k8s"], ...}')
        mock = MockLLMClient(responses=["ok1", "INVALID_JSON", "ok3"])
    """

    def __init__(self, response: str | list[str] = ""):
        self.responses = [response] if isinstance(response, str) else list(response)
        self.call_count = 0

    async def chat(self, prompt: str, max_tokens: int = 2000) -> str:
        idx = min(self.call_count, len(self.responses) - 1)
        self.call_count += 1
        if idx < 0:
            return ""
        return self.responses[idx]