from openai import OpenAI

from agentic.agents import Agent
from agentic.problem.coder.types import CoderPlannerInput, CoderPlannerOutput


def make_planner(client: OpenAI, model: str) -> Agent[CoderPlannerInput, CoderPlannerOutput]:
    """
    Planner decomposes a user-defined project into concrete subtasks.
    """
    planner_prompt = """
ROLE:
You are the Coder Planner. Break down the user-provided project into a sequence of small coding subtasks.

INPUT (PlannerInput JSON):
{
  "project_description": string,
  "feedback": string | null,
  "previous_task": { "language": "python" | "javascript", "specification": string, "requirements": [string, ...] } | null,
  "previous_worker_id": string | null,
  "random_seed": string | int | null
}

OUTPUT (PlannerOutput JSON):
{
  "task": {
    "language": "python" | "javascript",
    "specification": "<one subtask from the project>",
    "requirements": ["acceptance criterion 1", "acceptance criterion 2"]
  },
  "worker_id": "coder-worker"
}

GUIDELINES:
- Use project_description as the single source of truth. Do NOT invent unrelated tasks.
- Decompose the project into small, sequential pieces. Keep each specification narrowly scoped and achievable without external dependencies.
- Respect feedback: if a requirement failed, reissue the subtask with corrected requirements; otherwise, advance to the next unsatisfied piece.
- Align language with the project; avoid switching languages midstream unless feedback demands it.
- Requirements should be concrete, testable acceptance criteria (2-5 items) tied directly to the subtask.
- Always route worker_id = "coder-worker".
- No randomness: variation comes only from project_description, previous_task, and feedback.
- Strict JSON only; no explanation or extra fields.
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
