"""MiniMax LLM client (OpenAI protocol) + MockLLMClient for testing.

MiniMax M3 supports OpenAI-compatible API at https://api.minimaxi.com/v1.
Both M2.1 and M3 are reasoning models — they emit <think>...</think> blocks
before the actual content. Use `extractContent()` to strip them before JSON parsing.
This module provides:
- MiniMaxClient: real client using openai SDK
- MockLLMClient: for tests, accepts preset responses
- extractContent: static helper to strip reasoning blocks
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
    """OpenAI-protocol client for MiniMax M3.

    Endpoint: https://api.minimaxi.com/v1/chat/completions
    Auth: Bearer ${MINIMAX_API_KEY}
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://api.minimaxi.com/v1",
        model: str = "MiniMax-M3",
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