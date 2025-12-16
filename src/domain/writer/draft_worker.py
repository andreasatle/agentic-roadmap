from agentic.agents.openai import OpenAIAgent
from domain.writer.schemas import DraftWorkerInput, WriterWorkerOutput
from domain.writer.types import DraftSectionTask


PROMPT_DRAFT_WORKER = """ROLE:
You are the Writer Draft Worker.

You draft a brand-new section based strictly on the Planner's task JSON.
You do not plan, critique, or refine existing text.

INPUT FORMAT (from Planner):
{
  "task": {
    "kind": "draft_section",
    "section_name": "<name>",
    "purpose": "<reason this section exists>",
    "requirements": ["...", "..."]
  }
}

OUTPUT FORMAT (STRICT):
{
  "result": {
    "text": "<complete draft for the section>"
  }
}

RULES:
1. Output ONLY valid JSON with keys exactly as specified.
2. Write a polished, publication-ready section.
3. Satisfy every requirement; stay within scope.
4. No meta-commentary, no explanations, no code fences.
"""


def make_draft_worker(model: str) -> OpenAIAgent[DraftWorkerInput, WriterWorkerOutput]:
    """Create the dedicated draft worker; it only handles DraftSectionTask inputs."""
    base_agent = OpenAIAgent(
        name="writer-draft-worker",
        model=model,
        system_prompt=PROMPT_DRAFT_WORKER,
        input_schema=DraftWorkerInput,
        output_schema=WriterWorkerOutput,
        temperature=0.0,
    )

    class WriterDraftWorkerAgent:
        def __init__(self, agent: OpenAIAgent[DraftWorkerInput, WriterWorkerOutput]):
            self._agent = agent
            self.name = agent.name
            self.input_schema = agent.input_schema
            self.output_schema = agent.output_schema
            self.id = agent.id

        def __call__(self, user_input: str) -> str:
            try:
                worker_input = DraftWorkerInput.model_validate_json(user_input)
            except Exception as exc:
                raise RuntimeError("writer-draft-worker requires a DraftSectionTask input.") from exc
            if not isinstance(worker_input.task, DraftSectionTask):
                raise RuntimeError("writer-draft-worker received non-draft task.")

            raw_output = self._agent(user_input)
            output_model = WriterWorkerOutput.model_validate_json(raw_output)
            if not output_model.result.text:
                output_model.result.text = f"{worker_input.task.section_name}: {worker_input.task.purpose}"
            return output_model.model_dump_json()

    return WriterDraftWorkerAgent(base_agent)  # type: ignore[return-value]
