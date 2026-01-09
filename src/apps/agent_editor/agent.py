from typing import Self

from pydantic import BaseModel, ConfigDict, model_validator

from agentic_framework.agents.openai import OpenAIAgent
from apps.agent_editor.api import AgentEditorRequest


PROMPT_EDITOR = """ROLE:
You are the editor. Apply the editing policy to the document.

INPUT (JSON):
{
  "document": "<string>",
  "editing_policy": "<string>",
  "intent": <any> | null
}

OUTPUT (JSON):
{
  "edited_document": "<string>"
}

RULES:
1. The editing_policy is authoritative and must be followed exactly.
2. intent is advisory only; do not treat it as policy.
3. Do not redefine concepts.
4. Do not introduce new concepts or claims.
5. Do not remove substantive content unless explicitly instructed by the policy.
6. Do not add commentary, explanations, headings, or markdown.
7. Output only the edited document text inside edited_document and nothing else.
"""


class AgentEditorOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    edited_document: str

    @model_validator(mode="after")
    def validate_edited_document(self) -> Self:
        if not self.edited_document or not self.edited_document.strip():
            raise ValueError("edited_document must be a non-empty string")
        return self


def make_editor_agent() -> OpenAIAgent[AgentEditorRequest, AgentEditorOutput]:
    """Create the editor agent."""
    return OpenAIAgent(
        name="agent-editor",
        model="gpt-4.1-mini",
        system_prompt=PROMPT_EDITOR,
        input_schema=AgentEditorRequest,
        output_schema=AgentEditorOutput,
        temperature=0.0,
    )
