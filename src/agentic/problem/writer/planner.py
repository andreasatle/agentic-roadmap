from openai import OpenAI

from agentic.agents import Agent
from agentic.problem.writer.schemas import WriterPlannerInput, WriterPlannerOutput
from agentic.problem.writer.state import WriterState


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
  "domain": { ... }     // domain-specific snapshot
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
- If project_state is provided, you MAY use it to improve decisions.
- If project_state is absent or null, behave exactly as before.
- Never require state fields. Never fail if they are missing.

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
            problem_state = getattr(planner_input, "problem_state", None)
            raw = self._agent(user_input)
            try:
                output_model = self.output_schema.model_validate_json(raw)
            except Exception:
                return raw

            if isinstance(problem_state, WriterState):
                section_name = output_model.task.section_name
                if section_name in problem_state.sections:
                    alt_name = (
                        f"{section_name} (continued)"
                        if f"{section_name} (continued)" not in problem_state.sections
                        else f"{section_name} Part 2"
                    )
                    output_model.task.section_name = alt_name

            return output_model.model_dump_json()

    return WriterPlannerAgent(base_agent)  # type: ignore[return-value]
