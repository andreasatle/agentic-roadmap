from openai import OpenAI
from agentic.agents import Agent
from agentic.problem.arithmetic.types import (
    ArithmeticPlannerInput,
    ArithmeticPlannerOutput,
    WORKER_CAPABILITIES,
)


def make_planner(client: OpenAI, model: str) -> Agent[ArithmeticPlannerInput, ArithmeticPlannerOutput]:
    """
    Planner emits a single ArithmeticTask and routes it to a compatible worker.
    """
    worker_specs = "\n".join(
        f"- {worker_id}: supports {', '.join(sorted(spec.supported_ops))}"
        for worker_id, spec in sorted(WORKER_CAPABILITIES.items())
    )
    worker_options = " | ".join(f'"{worker_id}"' for worker_id in sorted(WORKER_CAPABILITIES))
    planner_prompt = """
ROLE:
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
"""
    return Agent(
        name="Planner",
        client=client,
        model=model,
        system_prompt=planner_prompt,
        input_schema=ArithmeticPlannerInput,
        output_schema=ArithmeticPlannerOutput,
        temperature=0.4,
    )
