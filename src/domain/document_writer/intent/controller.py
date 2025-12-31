from dataclasses import dataclass
import hashlib

from agentic.agents.openai import OpenAIAgent
from agentic.logging_config import get_logger
from agentic.protocols import AgentProtocol
from pydantic import BaseModel

from domain.document_writer.intent.types import IntentEnvelope

logger = get_logger("intent.adapter")

PROMPT_INTENT = """ROLE:
You are the Text → Intent adapter. You extract user intent signals into a structured IntentEnvelope.

INPUT:
{
  "text": "<raw user text>"
}

OUTPUT (STRICT JSON, IntentEnvelope fields only):
{
  "structural_intent": {
    "document_goal": string | null,
    "audience": string | null,
    "tone": string | null,
    "required_sections": [string, ...],
    "forbidden_sections": [string, ...]
  },
  "semantic_constraints": {
    "must_include": [string, ...],
    "must_avoid": [string, ...],
    "required_mentions": [string, ...]
  },
  "stylistic_preferences": {
    "humor_level": string | null,
    "formality": string | null,
    "narrative_voice": string | null
  }
}

RULES:
- Advisory only: do NOT create document structure, tasks, or ordering.
- No planning, no execution, no workflow decisions.
- Do NOT invent section hierarchy or ids; use labels only.
- Unknown fields are forbidden. Strict JSON only.
"""


class TextIntentInput(BaseModel):
    text: str


@dataclass
class TextIntentController:
    """Single-pass projection of raw text into IntentEnvelope; advisory-only."""

    agent: AgentProtocol[TextIntentInput, IntentEnvelope]

    def __call__(self, text: str) -> IntentEnvelope:
        input_model = TextIntentInput(text=text)
        raw = self.agent(input_model.model_dump_json())
        result = IntentEnvelope.model_validate_json(raw)
        logger.info(
            "intent_adapter_call",
            extra={
                "source": "text-intent-adapter",
                "input_hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                "model": getattr(self.agent, "model", ""),
            },
        )
        return result


def make_text_intent_controller(
    *,
    model: str = "gpt-4.1-mini",
) -> TextIntentController:
    base_agent = OpenAIAgent(
        name="TextIntentAdapter",
        model=model,
        system_prompt=PROMPT_INTENT,
        input_schema=TextIntentInput,
        output_schema=IntentEnvelope,
        temperature=0.0,
    )

    class AdapterAgent:
        def __init__(self, agent: OpenAIAgent[TextIntentInput, IntentEnvelope]):
            self._agent = agent
            self.name = agent.name
            self.input_schema = agent.input_schema
            self.output_schema = agent.output_schema
            self.id = agent.id
            self.model = getattr(agent, "model", "")

        def __call__(self, user_input: str) -> str:
            # Validate input before sending
            self.input_schema.model_validate_json(user_input)
            return self._agent(user_input)

    return TextIntentController(agent=AdapterAgent(base_agent))
