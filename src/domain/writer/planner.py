from agentic.agents.openai import OpenAIAgent
from domain.writer.schemas import WriterPlannerInput, WriterPlannerOutput
from domain.writer.types import DraftSectionTask, RefineSectionTask


PROMPT_PLANNER = """ROLE:
You are the Writer Planner VALIDATOR.

You DO NOT plan, choose sections, decide operations, or write content.
Your only job:
1) Validate the incoming task references an existing section in the provided structure.
2) Route the task to the correct worker based on task.kind.

INPUT (from Supervisor / CLI):
{
  "task": { ... },           // DraftSectionTask or RefineSectionTask
  "project_state": {
    "project": { ... },
    "domain": {
      "structure": {
        "sections": ["..."]
      }
    }
  } | null
}

OUTPUT (STRICT JSON ONLY):
{
  "task": { ...same as input... },
  "worker_id": "writer-draft-worker | writer-refine-worker"
}

RULES:
- No inference, no modification of the task.
- Reject if the task section is not in the provided structure.
- Always return exactly one task and one worker_id.
- No commentary or explanations.
"""


def make_planner(model: str) -> OpenAIAgent[WriterPlannerInput, WriterPlannerOutput]:
    """
    Planner only validates structure membership and routes writer tasks to the
    appropriate worker (draft vs refine). It never alters tasks or invents content.
    """
    base_agent = OpenAIAgent(
        name="WriterPlanner",
        model=model,
        system_prompt=PROMPT_PLANNER,
        input_schema=WriterPlannerInput,
        output_schema=WriterPlannerOutput,
        temperature=0.0,
    )

    class WriterPlannerAgent:
        def __init__(self, agent: OpenAIAgent[WriterPlannerInput, WriterPlannerOutput]):
            self._agent = agent
            self.name = agent.name
            self.input_schema = agent.input_schema
            self.output_schema = agent.output_schema
            self.id = agent.id

        def __call__(self, user_input: str) -> str:
            planner_input = self.input_schema.model_validate_json(user_input)
            if planner_input.task is None:
                raise RuntimeError("Writer planner requires an explicit task.")
            domain_state = planner_input.project_state
            structure = domain_state.structure if domain_state else None
            sections = structure.sections if structure else None
            if not sections:
                raise RuntimeError("Writer planner requires explicit structure with at least one section.")
            task_section = getattr(planner_input.task, "section_name", None)
            if task_section not in sections:
                raise RuntimeError(f"Writer planner cannot invent section '{task_section}'.")
            if isinstance(planner_input.task, DraftSectionTask):
                worker_id = "writer-draft-worker"
            elif isinstance(planner_input.task, RefineSectionTask):
                worker_id = "writer-refine-worker"
            else:
                raise RuntimeError("Unsupported writer task type.")
            output_model = WriterPlannerOutput(task=planner_input.task, worker_id=worker_id)
            return output_model.model_dump_json()

    return WriterPlannerAgent(base_agent)  # type: ignore[return-value]
