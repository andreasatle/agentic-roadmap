import json
from openai import OpenAI

from agentic.agents import Agent
from domain.writer.schemas import WriterPlannerInput, WriterPlannerOutput
from domain.writer.types import WriterTask
from domain.writer.state import WriterState


PROMPT_PLANNER = """ROLE:
You are the Planner in a Planner–Worker–Critic loop. 
Your sole responsibility is to decompose the high-level goal into a precise, 
minimal subtask for the Worker. You do not write any prose. You do not perform 
execution. You shape the work.

HIGH-LEVEL GOAL (DEFINED BY SUPERVISOR):
Write a whitepaper-style article describing how the Planner–Worker–Critic framework 
emerged during the development of an agentic coding system, including the 
meta-realization that the same framework was used to build itself, and the transition 
to a meta-meta collaborative workflow.

OPTIONAL INPUT FIELD:
"project_state": {
  "project": { ... },   // global ProjectState snapshot
  "domain": { ... }     // writer-specific state snapshot
} | null

THE ARTICLE MUST:
- be structured, coherent, and academically toned
- include the origin story: coding project → request for codex prompts → 
  emergence of Planner–Worker–Critic pattern
- describe the bootstrap/snapshot method to inject authoritative state
- discuss the philosophical angle: “the framework taught me how to work”
- include the anecdote of realizing that introducing ProjectState coincided 
  with introducing explicit conversational state
- include the quotation: “In theory there is no difference between theory and practice, 
  but in practice there is.”
- highlight the self-reference and recursion themes
- be suitable for GitHub or Medium publication

PLANNER OUTPUT FORMAT (STRICT JSON):
{
  "task": {
    "section_name": "<name of the first section to be written>",
    "purpose": "<why this section is needed>",
    "requirements": [
       "<acceptance criterion 1>",
       "<acceptance criterion 2>",
       "<etc>"
    ]
  }
}
  
PLANNER RULES:
1. Produce exactly ONE subtask: the first section to write.
2. Begin with the section that logically anchors the entire paper.
3. Requirements must be concrete, testable, and minimal.
4. Avoid specifying content; specify only structure and constraints.
5. Avoid creativity beyond task decomposition.
6. No commentary outside the JSON.

STATE USAGE:
- If project_state.domain contains an outline, a working topic, or prior section
  choices, use that information to continue the writing task rather than starting
  from scratch.
- If project_state.project includes the last plan or last result, use it to avoid
  repeating the same high-level planning decisions.
- If project_state is missing or null, behave exactly as before.
- Never require project_state fields; prompts must remain fully valid without it.

Generate the first plan now.
"""


def make_planner(client: OpenAI, model: str) -> Agent[WriterPlannerInput, WriterPlannerOutput]:
    """
    MVP planner: emits a single WriterTask routed to the writer worker.
    """
    base_agent = Agent(
        name="WriterPlanner",
        client=client,
        model=model,
        system_prompt=PROMPT_PLANNER,
        input_schema=WriterPlannerInput,
        output_schema=WriterPlannerOutput,
        temperature=0.0,
    )

    class WriterPlannerAgent:
        def __init__(self, agent: Agent[WriterPlannerInput, WriterPlannerOutput]):
            self._agent = agent
            self.name = agent.name
            self.input_schema = agent.input_schema
            self.output_schema = agent.output_schema
            self.id = agent.id

        def __call__(self, user_input: str) -> str:
            planner_input = WriterPlannerInput.model_validate_json(user_input)
            try:
                raw_payload = json.loads(user_input)
            except Exception:
                raw_payload = {}
            raw = self._agent(user_input)
            try:
                payload = json.loads(raw)
            except Exception:
                return raw
            task_obj = None
            match payload:
                case dict():
                    match payload.get("task"), payload.get("next_task"):
                        case dict() as t, _:
                            task_obj = t
                            task_key = "task"
                        case _, dict() as nt:
                            task_obj = nt
                            task_key = "next_task"
                        case _:
                            task_key = None
                    if task_obj is not None and "operation" not in task_obj:
                        task_obj["operation"] = "initial_draft"
                        if task_key:
                            payload[task_key] = task_obj
                    raw = json.dumps(payload)
                case _:
                    pass
            try:
                output_model = self.output_schema.model_validate_json(raw)
            except Exception:
                return raw

            state = getattr(planner_input, "project_state", None)
            completed_sections: list[str] = []
            match state:
                case WriterState():
                    if getattr(state, "sections", None):
                        completed_sections = list(state.sections)
                case _:
                    domain_state = None
                    if state is not None:
                        domain_state = state.domain_state.get("writer")
                    if domain_state and getattr(domain_state, "completed_sections", None):
                        completed_sections = list(domain_state.completed_sections)

            base_task = getattr(planner_input, "task", None) or getattr(output_model, "task", None)
            if base_task is None:
                return raw
            section_name = base_task.section_name
            attempts = completed_sections.count(section_name)

            if attempts == 0:
                operation = "initial_draft"
            elif attempts == 1:
                operation = "refine_draft"
            else:
                operation = "finalize_draft"

            new_task = WriterTask(
                section_name=section_name,
                purpose=base_task.purpose,
                requirements=base_task.requirements,
                operation=operation,
            )
            output_model.task = new_task

            return output_model.model_dump_json()

    return WriterPlannerAgent(base_agent)  # type: ignore[return-value]
