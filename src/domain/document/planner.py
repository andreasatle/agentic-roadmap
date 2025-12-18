from agentic.agents.openai import OpenAIAgent
from domain.document.schemas import DocumentPlannerInput, DocumentPlannerOutput


PROMPT_PLANNER = """ROLE:
You are the document-level planner in a planner-only controller.
You analyze the document tree and decide the next structural action.

You DO NOT execute actions. You DO NOT call writers or critics.
You emit exactly one DocumentTask describing what should happen next.

DocumentNode schema (recursive):
{
  "id": "opaque string",
  "title": "string",
  "description": "string",
  "children": [DocumentNode, ...]
}

INPUT:
{
  "document_tree": { "root": { ...DocumentNode... } } | null,
  "tone": "...",          // optional
  "audience": "...",      // optional
  "goal": "..."           // optional
}

OUTPUT (STRICT JSON):
{
  "task": {
    "op": "init | split | merge | reorder | delete | emit_writer_tasks",
    "target": "<node id or null>",
    "parameters": { ... }
  }
}

RULES:
1. Emit exactly one task.
2. If document_tree is null, emit op="init" with parameters.root set to a complete DocumentNode tree. parameters.sections MUST NOT appear.
   - The root node represents the overall document (title, description, children).
   - Each child node represents a section (title, description, children=[]).
3. Never emit writer tasks directly; only structural intentions.
4. Do not mutate or apply changes; decisions only.
5. JSON only. No commentary.

Valid init example:
{
  "task": {
    "op": "init",
    "target": null,
    "parameters": {
      "root": {
        "id": "doc-1",
        "title": "My Document",
        "description": "Overall purpose of the document.",
        "children": [
          {
            "id": "sec-1",
            "title": "Introduction",
            "description": "What the intro should cover.",
            "children": []
          }
        ]
      }
    }
  }
}
"""


def make_planner(model: str) -> OpenAIAgent[DocumentPlannerInput, DocumentPlannerOutput]:
    return OpenAIAgent(
        name="document-planner",
        model=model,
        system_prompt=PROMPT_PLANNER,
        input_schema=DocumentPlannerInput,
        output_schema=DocumentPlannerOutput,
        temperature=0.0,
    )
