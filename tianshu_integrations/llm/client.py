"""MiniMax LLM client (OpenAI protocol) + MockLLMClient for testing.

MiniMax M3 supports OpenAI-compatible API at https://api.minimaxi.com/v1.
This module provides:
- MiniMaxClient: real client using openai SDK
- MockLLMClient: for tests, accepts preset responses
"""

import os

from openai import AsyncOpenAI


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
        """Call MiniMax M3 chat completion. Returns the assistant content."""
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