from __future__ import annotations

from dataclasses import dataclass
from typing import Generic
from openai import OpenAI

from .protocols import InputSchema, OutputSchema


# ============================================================
# Generic Agent Wrapper
# ============================================================

@dataclass
class Agent(Generic[InputSchema, OutputSchema]):
    """
    Generic LLM-based agent.

    The Supervisor is the trusted layer. Agents are untrusted.
    Their only job is:
        input_json  -> LLM -> validated_output_json
    """
    name: str
    client: OpenAI
    model: str
    system_prompt: str
    input_schema: type[InputSchema]
    output_schema: type[OutputSchema]
    temperature: float = 0.0

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
