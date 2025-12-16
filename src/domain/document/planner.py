from openai import OpenAI

from agentic.agents.openai import OpenAIAgent
from domain.document.schemas import DocumentPlannerInput, DocumentPlannerOutput


PROMPT_PLANNER = """ROLE:
You are the document-level planner in a planner-only supervisor.
You analyze document structure and decide the next structural action.

You DO NOT execute actions. You DO NOT call writers or critics.
You emit exactly one DocumentTask describing what should happen next.

INPUT:
{
  "document_state": { "sections": [...] } | null,
  "tone": "...",          // optional
  "audience": "...",      // optional
  "goal": "..."           // optional
}

OUTPUT (STRICT JSON):
{
  "task": {
    "op": "init | split | merge | reorder | delete | emit_writer_tasks",
    "target": "<section name or null>",
    "parameters": { ... }
  }
}

RULES:
1. Emit exactly one task.
2. If document_state is null, emit op="init" with parameters.sections listing an initial outline.
3. Never emit writer tasks directly; only structural intentions.
4. Do not mutate or apply changes; decisions only.
5. JSON only. No commentary.
"""


def make_planner(client: OpenAI, model: str) -> OpenAIAgent[DocumentPlannerInput, DocumentPlannerOutput]:
    return OpenAIAgent(
        name="document-planner",
        client=client,
        model=model,
        system_prompt=PROMPT_PLANNER,
        input_schema=DocumentPlannerInput,
        output_schema=DocumentPlannerOutput,
        temperature=0.0,
    )
