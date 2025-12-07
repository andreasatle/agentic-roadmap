from openai import OpenAI

from agentic.agents import Agent
from agentic.problem.coder.types import CoderCriticInput, CoderCriticOutput


def make_critic(client: OpenAI, model: str) -> Agent[CoderCriticInput, CoderCriticOutput]:
    """
    Critic validates that the code meets the specification and requirements.
    """
    critic_prompt = """
ROLE:
You are the Coder Critic. Judge whether the worker's code satisfies the planned coding task.

INPUT (CriticInput JSON):
{
  "plan": {
    "language": "python" | "javascript",
    "specification": string,
    "requirements": [string, ...]
  },
  "worker_answer": { "code": string } | null
}

OUTPUT (Decision JSON):
{
  "decision": "ACCEPT" | "REJECT",
  "feedback": string | null
}

RULES:
1) If worker_answer is missing or code is empty, REJECT with feedback requesting code.
2) If the code is not in plan.language, REJECT with feedback to use the correct language.
3) Verify the code addresses each requirement; if any are missing, REJECT with specific missing items.
4) On REJECT, provide actionable feedback (e.g., "Add handling for empty input; use Python not JavaScript").
5) On ACCEPT, set feedback to null.
6) Strict JSON only.
"""
    return Agent(
        name="CoderCritic",
        client=client,
        model=model,
        system_prompt=critic_prompt,
        input_schema=CoderCriticInput,
        output_schema=CoderCriticOutput,
        temperature=0.0,
    )
