"""
Text Prompt Refiner Contract

- Input: raw user text (str).
- Output: refined user text (str).
- Transformation is semantic-preserving, non-authoritative, and advisory-only.
- The refiner MUST NOT invent intent or meaning; it only normalizes the supplied text.
- The refiner does NOT plan, execute, extract intent, create structure, or generate documents.
"""
import hashlib

from agentic.agents.openai import OpenAIAgent
from agentic.logging_config import get_logger
from agentic.protocols import AgentProtocol
from pydantic import BaseModel


class TextPromptRefinerInput(BaseModel):
    """Raw user text input for the Text Prompt Refiner; sole, authority-free input."""

    text: str


PROMPT_TEXT_REFINER = """ROLE:
You rewrite raw user text into a clearer version of the same intent.

RULES (DO):
- Preserve meaning exactly; rephrase only to clarify.
- Expose ambiguities explicitly instead of guessing.
- Preserve first-person voice, uncertainty, and tone.

RULES (DO NOT):
- Do NOT add goals, ideas, opinions, or examples.
- Do NOT remove core concerns or resolve ambiguity by guessing.
- Do NOT plan, decide structure, extract intent, or generate articles.
- Do NOT explain concepts or define terminology.
- Do NOT use headings, lists, or structured formats.

OUTPUT:
- Return ONLY refined plain prose of the same intent; no commentary or metadata."""


class TextPromptRefinerController:
    """Single-pass refiner: raw text → clarified text; semantic-preserving and advisory-only."""

    def __init__(self, *, agent: AgentProtocol[TextPromptRefinerInput, str]) -> None:
        self.agent = agent
        self.logger = get_logger("text_prompt_refiner")

    def __call__(self, text: str) -> str:
        input_model = TextPromptRefinerInput(text=text)
        raw = self.agent(input_model.model_dump_json())
        self.logger.info(
            "text_prompt_refiner_call",
            extra={
                "controller": "TextPromptRefinerController",
                "input_hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                "model": getattr(self.agent, "model", ""),
            },
        )
        return raw


def make_text_prompt_refiner_controller(
    *,
    model: str = "gpt-4.1-mini",
) -> TextPromptRefinerController:
    base_agent = OpenAIAgent(
        name="TextPromptRefiner",
        model=model,
        system_prompt=PROMPT_TEXT_REFINER,
        input_schema=TextPromptRefinerInput,
        output_schema=None,  # type: ignore[arg-type]
        temperature=0.0,
    )

    class RefinerAgent:
        def __init__(self, agent: OpenAIAgent):
            self._agent = agent
            self.name = agent.name
            self.input_schema = agent.input_schema
            self.output_schema = agent.output_schema
            self.id = agent.id
            self.model = getattr(agent, "model", "")

        def __call__(self, user_input: str) -> str:
            self.input_schema.model_validate_json(user_input)
            resp = self._agent.client.chat.completions.create(
                model=self._agent.model,
                temperature=self._agent.temperature,
                messages=[
                    {"role": "system", "content": self._agent.system_prompt.strip()},
                    {"role": "user", "content": user_input},
                ],
            )
            message = resp.choices[0].message
            return (message.content or "").strip()

    return TextPromptRefinerController(agent=RefinerAgent(base_agent))
