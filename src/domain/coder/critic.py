from openai import OpenAI

from agentic.agents import Agent
from domain.coder.types import CoderCriticInput, CoderCriticOutput


PROMPT_CRITIC = """ROLE:
You are the Coder Critic. Judge whether the worker's code satisfies the planned subtask and aligns with the project.

INPUT (CriticInput JSON):
{
  "plan": {
    "language": "python" | "javascript",
    "specification": string,
    "requirements": [string, ...]
  },
  "worker_answer": { "code": string } | null,
  "project_description": string

  Optional:
  "project_state": {
    "project": { ... },
    "domain": { ... }
  } | null
}

OUTPUT (Decision JSON):
{
  "decision": "ACCEPT" | "REJECT",
  "feedback": null | {
    "kind": "EMPTY_RESULT" | "LANGUAGE_MISMATCH" | "TASK_INCOMPLETE" | "SCOPE_ERROR" | "OTHER",
    "message": string
  }
}

RULES:
1) If worker_answer is missing or code is empty, REJECT with feedback.kind="EMPTY_RESULT" and an actionable message requesting the subtask implementation.
2) If the code is not in plan.language, REJECT with feedback.kind="LANGUAGE_MISMATCH" and guidance to use the correct language.
3) Verify the code addresses EVERY requirement; if any are missing, REJECT with feedback.kind="TASK_INCOMPLETE" and specific, actionable feedback.
4) Ensure the code stays within the subtask scope and aligns with the project_description; reject scope creep or unrelated features with feedback.kind="SCOPE_ERROR".
5) On REJECT, feedback must be an object with both kind and message; provide actionable guidance. On ACCEPT, feedback = null.
6) Strict JSON only.

STATE USAGE:
- You may consider project_state to improve evaluation, but must operate correctly when it is null or missing.
"""


def make_critic(client: OpenAI, model: str) -> Agent[CoderCriticInput, CoderCriticOutput]:
    """
    Critic validates that the code meets the project-aligned specification and requirements.
    """
    return Agent(
        name="CoderCritic",
        client=client,
        model=model,
        system_prompt=PROMPT_CRITIC,
        input_schema=CoderCriticInput,
        output_schema=CoderCriticOutput,
        temperature=0.0,
    )
