from openai import OpenAI
from agentic.agents import Agent
from agentic.problem.arithmetic.types import ArithmeticPlannerInput, ArithmeticPlannerOutput

def make_planner(client: OpenAI, model: str) -> Agent[ArithmeticPlannerInput, ArithmeticPlannerOutput]:
    """
    Planner emits a single Task.
    Must match PlannerOutput == Task schema.
    """
    planner_prompt = """
ROLE:
You are the Planner.
Emit a single arithmetic Task.

INPUT:
- You are called with an empty JSON object: {}.

OUTPUT (JSON ONLY, NO TEXT AROUND IT):
{
  "task": {
    "op": "ADD" | "SUB" | "MUL",
    "a": <int>,
    "b": <int>
  },
  "worker_id": "arithmetic-worker"
}

RULES:
- Choose op uniformly from {"ADD","SUB","MUL"}.
- Choose a and b uniformly from [1, 20].
- Emit ONLY valid JSON matching the Task schema.
- No comments, no trailing commas, no extra fields.
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
