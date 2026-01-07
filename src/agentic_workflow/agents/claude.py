from dataclasses import dataclass, field
from typing import Generic, TypeVar, Final
from uuid import uuid4
from anthropic import Anthropic

InT = TypeVar("InT")
OutT = TypeVar("OutT")


@dataclass
class ClaudeAgent(Generic[InT, OutT]):
    # REQUIRED by AgentProtocol
    name: str
    input_schema: type[InT]
    output_schema: type[OutT]

    # Provider-specific
    model: str
    system_prompt: str
    temperature: float = 0.0
    max_tokens: int = 4096
    _client: Anthropic | None = field(default=None, repr=False)

    id: Final[str] = field(default_factory=lambda: str(uuid4()))

    @property
    def client(self) -> Anthropic:
        if self._client is None:
            self._client = Anthropic()
        return self._client

    def __call__(self, input_json: str) -> str:
        response = self.client.messages.create(
            model=self.model,
            temperature=self.temperature, 
            max_tokens=self.max_tokens,
            system=self.system_prompt,
            messages=[{"role": "user", "content": input_json}],
        )

        if not response.content:
            raise RuntimeError("Claude returned empty response")

        block = response.content[0]

        if not hasattr(block, "text"):
            raise RuntimeError("Claude response missing text")

        return block.text.strip()
