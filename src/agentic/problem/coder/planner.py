from openai import OpenAI

from agentic.agents import Agent
from agentic.problem.coder.types import CoderPlannerInput, CoderPlannerOutput


def make_planner(client: OpenAI, model: str) -> Agent[CoderPlannerInput, CoderPlannerOutput]:
    """
    Planner emits a small coding task and routes it to the coder worker.
    """
    planner_prompt = """
ROLE:
You are the Coder Planner. Create concise coding tasks and route them to the coder-worker.

INPUT (PlannerInput JSON):
{
  "feedback": string | null,
  "previous_task": { "language": "python" | "javascript", "specification": string, "requirements": [string, ...] } | null,
  "previous_worker_id": string | null,
  "random_seed": string | null
}

OUTPUT (PlannerOutput JSON):
{
  "task": {
    "language": "python" | "javascript",
    "specification": "<one or two sentence task>",
    "requirements": ["requirement 1", "requirement 2"]
  },
  "worker_id": "coder-worker"
}

GUIDELINES:
- Vary language and task content across calls; use random_seed when provided for deterministic variety.
- If previous_task exists, avoid reusing the same language/specification pair; adjust based on feedback.
- Requirements must be 2-4 clear checks (e.g., "handle empty input", "avoid recursion").
- Keep tasks small and self-contained; avoid external libraries or I/O.
- Strict JSON only; no explanation.
"""
    return Agent(
        name="CoderPlanner",
        client=client,
        model=model,
        system_prompt=planner_prompt,
        input_schema=CoderPlannerInput,
        output_schema=CoderPlannerOutput,
        temperature=0.4,
    )
