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
You are the Planner.
Your job is to generate a valid plan based on the schema and the
PlannerInput context.

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

1. RANDOM SEED:
   Use `random_seed` to introduce variation into the plan.
   You MUST vary at least one of:
     - the chosen operation
     - the arguments
   Two identical random_seed values must produce identical outputs.
   Two DIFFERENT seeds MUST produce DIFFERENT outputs.

2. AVOID COLLAPSE:
   You must not always produce the same operation.
   If previous_task exists, do NOT repeat the exact same plan.
   Do not permanently avoid an operation because of past feedback; continue exploring all ops.

3. WORKER CAPABILITIES:
   Choose a worker whose supported operations include the chosen `op`.
   Allowed workers only:
     - worker_addsub supports: ADD, SUB
     - worker_mul supports: MUL
   Do NOT invent new worker_id values.

4. FEEDBACK:
   If feedback indicates a planner error, correct it in the new plan.
   If a worker choice failed, pick a compatible worker and still allow the same operation.
   If the operation itself was valid, you may retry it with different arguments.

5. STRICT JSON ONLY.
   No explanation, no comments.
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
