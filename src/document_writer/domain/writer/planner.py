from agentic_workflow.agents.openai import OpenAIAgent
from document_writer.domain.writer.schemas import WriterPlannerInput, WriterPlannerOutput
from document_writer.domain.writer.types import DraftSectionTask, RefineSectionTask


PROMPT_PLANNER = """ROLE:
You are the Writer Planner VALIDATOR.

You DO NOT plan, invent sections, or write content.
Your only job:
1) Validate the incoming task payload is well-formed.
2) Route the task to the correct worker based on task.kind.

INPUT (from Controller / CLI):
{ "task": { ... } }

OUTPUT (STRICT JSON ONLY):
{ "task": { ...same as input... }, "worker_id": "writer-draft-worker | writer-refine-worker" }

RULES:
- No inference or alteration of the task.
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
            try:
                planner_input = self.input_schema.model_validate_json(user_input)
            except Exception as exc:
                raise RuntimeError("Writer planner requires an explicit task.") from exc
            if planner_input.task is None:
                raise RuntimeError("Writer planner requires an explicit task.")

            match planner_input.task:
                case DraftSectionTask():
                    worker_id = "writer-draft-worker"
                case RefineSectionTask():
                    worker_id = "writer-refine-worker"
                case _:
                    raise RuntimeError("Unsupported writer task type.")

            output_model = WriterPlannerOutput(task=planner_input.task, worker_id=worker_id)

            return output_model.model_dump_json()

    return WriterPlannerAgent(base_agent)  # type: ignore[return-value]
