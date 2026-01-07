from agentic_workflow.agents.openai import OpenAIAgent
from experiments.arithmetic.types import (
    ArithmeticPlannerInput,
    ArithmeticPlannerOutput,
)


PROMPT_PLANNER = """ROLE:
You are the Arithmetic Planner.
Use the capability table to route tasks to the correct worker.

Workers and their capabilities:
- worker_addsub → supports ["ADD", "SUB"]
- worker_mul → supports ["MUL"]

INPUT FORMAT (PlannerInput):
{
  "feedback": string | null,
  "previous_task": { ... } | null,
  "previous_worker_id": string | null,
  "random_seed": string | null

  Optional field:
  "project_state": {
    "project": { ... },   // global ProjectState snapshot
    "domain": { ... }     // domain-specific snapshot
  } | null
}

OUTPUT FORMAT (PlannerOutput):
{
  "task": {
    "op": "ADD" | "SUB" | "MUL",
    "a": int,
    "b": int
  },
  "worker_id": "worker_addsub" | "worker_mul"
}

RULES:

1) CAPABILITY ROUTING:
   - NEVER choose worker_mul for ADD or SUB.
   - NEVER choose worker_addsub for MUL.
   - You MUST use the capability table above.

2) VARIATION:
   - Choose varied operations and arguments; avoid repeating the same (op, a, b) triple across runs.
   - Use random_seed (if present) to drive deterministic variation.
   - If previous_task exists, prefer a different op or different numbers.

3) FEEDBACK HANDLING:
   - If feedback indicates wrong worker, fix the worker_id according to the table.
   - If feedback indicates wrong math, adjust op or numbers accordingly.

4) OUTPUT:
   - Strict JSON only; no comments or extra fields.

STATE USAGE:
- If project_state is provided, you MAY use it to improve decisions.
- If project_state is absent or null, behave exactly as before.
- Never require state fields. Never fail if they are missing.
"""


def make_planner(model: str) -> OpenAIAgent[ArithmeticPlannerInput, ArithmeticPlannerOutput]:
    """
    Planner emits a single ArithmeticTask and routes it to a compatible worker.
    """
    base_agent = OpenAIAgent(
        name="Planner",
        model=model,
        system_prompt=PROMPT_PLANNER,
        input_schema=ArithmeticPlannerInput,
        output_schema=ArithmeticPlannerOutput,
        temperature=0.4,
    )

    class ArithmeticPlannerAgent:
        def __init__(self, agent: OpenAIAgent[ArithmeticPlannerInput, ArithmeticPlannerOutput]):
            self._agent = agent
            self.name = agent.name
            self.input_schema = agent.input_schema
            self.output_schema = agent.output_schema
            self.id = agent.id

        def __call__(self, user_input: str) -> str:
            planner_input = self.input_schema.model_validate_json(user_input)
            task = planner_input.task
            if task.op == "MUL":
                worker_id = "worker_mul"
            elif task.op in {"ADD", "SUB"}:
                worker_id = "worker_addsub"
            else:
                raise RuntimeError("Unsupported arithmetic op")
            output_model = ArithmeticPlannerOutput(task=task, worker_id=worker_id)
            return output_model.model_dump_json()

    return ArithmeticPlannerAgent(base_agent)  # type: ignore[return-value]
