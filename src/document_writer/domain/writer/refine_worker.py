from agentic_workflow.agents.openai import OpenAIAgent
from document_writer.domain.writer.schemas import RefineWorkerInput, WriterWorkerOutput
from document_writer.domain.writer.types import RefineSectionTask


PROMPT_REFINE_WORKER = """ROLE:
You are the Writer Refine Worker.

You refine an existing section using the Planner's task JSON.
You do not plan, critique, or manage state beyond the given requirements.

INPUT FORMAT (from Planner):
{
  "task": {
    "kind": "refine_section",
    "section_name": "<name>",
    "purpose": "<reason this section exists>",
    "requirements": ["...", "..."],
    "defines": ["<concept-id>", "..."],
    "assumes": ["<concept-id>", "..."]
  }
}

OUTPUT FORMAT (STRICT):
{
  "result": {
    "text": "<section_name>:\\n<refined section text>"
  }
}

RULES:
1. Output ONLY valid JSON with keys exactly as specified.
2. Begin result.text with the exact section_name followed by a colon and newline.
3. Elevate clarity, cohesion, and completeness as guided by the requirements.
4. Stay within scope; avoid new topics unless explicitly requested.
5. Define ONLY the concepts listed in defines.
6. DO NOT define any concepts listed in assumes.
7. Do NOT infer whether a concept is already defined.
8. If a concept is neither in defines nor assumes, do not define it.
9. No meta-commentary, no explanations, no code fences.
10. Concept authority enforcement (assumes):
    - If a concept appears in assumes, you MUST NOT define it, restate what it is, or use definitional language such as:
      “X is…”, “X refers to…”, “X can be understood as…”.
    - Assumed concepts MUST be treated as already defined elsewhere.
    - When referencing an assumed concept, reference it implicitly or use phrasing such as “as previously defined” or “as introduced earlier”.
    - Definitional explanations are permitted ONLY for concepts listed in defines.
"""


def make_refine_worker(model: str) -> OpenAIAgent[RefineWorkerInput, WriterWorkerOutput]:
    """Create the dedicated refine worker; it only handles RefineSectionTask inputs."""
    base_agent = OpenAIAgent(
        name="writer-refine-worker",
        model=model,
        system_prompt=PROMPT_REFINE_WORKER,
        input_schema=RefineWorkerInput,
        output_schema=WriterWorkerOutput,
        temperature=0.0,
    )

    class WriterRefineWorkerAgent:
        def __init__(self, agent: OpenAIAgent[RefineWorkerInput, WriterWorkerOutput]):
            self._agent = agent
            self.name = agent.name
            self.input_schema = agent.input_schema
            self.output_schema = agent.output_schema
            self.id = agent.id

        def __call__(self, user_input: str) -> str:
            try:
                worker_input = RefineWorkerInput.model_validate_json(user_input)
            except Exception as exc:
                raise RuntimeError("writer-refine-worker requires a RefineSectionTask input.") from exc
            if not isinstance(worker_input.task, RefineSectionTask):
                raise RuntimeError("writer-refine-worker received non-refine task.")

            raw_output = self._agent(user_input)
            output_model = WriterWorkerOutput.model_validate_json(raw_output)
            if not output_model.result.text:
                output_model.result.text = f"{worker_input.task.section_name}: {worker_input.task.purpose}"
            return output_model.model_dump_json()

    return WriterRefineWorkerAgent(base_agent)  # type: ignore[return-value]
