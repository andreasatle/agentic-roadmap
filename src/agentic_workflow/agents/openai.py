from dataclasses import dataclass, field
from typing import Generic, Final
from uuid import uuid4
from openai import OpenAI

from agentic_workflow.protocols import InputSchema, OutputSchema


@dataclass
class OpenAIAgent(Generic[InputSchema, OutputSchema]):
    """
    Generic LLM-based agent.

    The Controller is the trusted layer. Agents are untrusted.
    Their only job is:
        input_json  -> LLM -> validated_output_json
    """
    name: str
    model: str
    system_prompt: str
    input_schema: type[InputSchema]
    output_schema: type[OutputSchema]
    _client: OpenAI | None = field(default=None, repr=False)
    temperature: float = 0.0
    id: Final[str] = field(default_factory=lambda: str(uuid4()))

    @property
    def client(self) -> OpenAI:
        if self._client is None:
            self._client = OpenAI()
        return self._client

    def __call__(self, user_input: str) -> str:
        """
        user_input is already JSON (input_schema.model_dump_json()).
        We always enforce json_object output.
        """
        resp = self.client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": self.system_prompt.strip()},
                {"role": "user", "content": user_input},
            ],
        )
        message = resp.choices[0].message
        return (message.content or "").strip()
