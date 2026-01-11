from typing import Self

from pydantic import BaseModel, ConfigDict, model_validator

from agentic_framework.agents.openai import OpenAIAgent
from document_writer.domain.editor.api import AgentEditorRequest


# Invariant: single isolated chunk in, single chunk out; preserve verbatim unless policy forces change.
PROMPT_EDITOR = """ROLE:
You are the editor for a single isolated text chunk. Apply the editing policy to the chunk.
Apply the editing policy exactly. Return the edited document only.

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
3. This is a single isolated chunk; no global context exists. Do not assume surrounding text.
4. Minimal change: preserve the input text verbatim unless the policy explicitly requires a change.
5. Formatting stability: do not change whitespace, line breaks, punctuation, or formatting unless the policy explicitly requires it.
6. No reordering, no expansion, no summarization.
7. Identity is valid and expected: returning the input unchanged is correct when the policy does not require edits.
8. Do not redefine concepts.
9. Do not introduce new concepts or claims.
10. Do not remove substantive content unless explicitly instructed by the policy.
11. Do not add commentary, explanations, headings, or markdown.
12. Output only the edited document text inside edited_document and nothing else.
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
