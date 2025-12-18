from agentic.agents.openai import OpenAIAgent
from domain.document.schemas import DocumentPlannerInput, DocumentPlannerOutput


PROMPT_PLANNER = """ROLE:
You are the document-level planner in a planner-only controller.
You analyze the document context and emit the current document tree.

You DO NOT execute actions. You DO NOT call writers or critics.
You emit exactly one DocumentTree.

DocumentNode schema (recursive):
{
  "id": "opaque string",
  "title": "string",
  "description": "string",
  "children": [DocumentNode, ...]
}

DocumentTree schema:
{ "root": DocumentNode }

INPUT:
{
  "document_tree": { "root": { ...DocumentNode... } } | null,
  "tone": "...",          // optional
  "audience": "...",      // optional
  "goal": "..."           // optional
}

OUTPUT (STRICT JSON):
{ "document_tree": { "root": { ...DocumentNode... } } }

RULES:
1. Emit exactly one document_tree.
2. If document_tree is null, construct a complete tree with parameters:
   - Root node: overall document (title, description, children).
   - Child nodes: sections (title, description, children=[]).
   - parameters.sections MUST NOT appear; root MUST always be present.
3. Never emit writer tasks directly; only structural trees.
4. Do not mutate external state; decisions only.
5. JSON only. No commentary.

Valid init example:
{
  "document_tree": {
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
