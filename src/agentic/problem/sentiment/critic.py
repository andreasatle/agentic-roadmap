from openai import OpenAI

from agentic.agents import Agent
from agentic.problem.sentiment.types import SentimentCriticInput, SentimentCriticOutput


PROMPT_CRITIC = """ROLE:
You are the Sentiment Critic. Compare the worker's classification against the plan's target sentiment.

INPUT (CriticInput JSON):
{
  "plan": { "text": string, "target_sentiment": "POSITIVE" | "NEGATIVE" | "NEUTRAL" },
  "worker_answer": { "sentiment": "POSITIVE" | "NEGATIVE" | "NEUTRAL" } | null

  Optional:
  "project_state": {
    "project": { ... },
    "domain": { ... }
  } | null
}

OUTPUT (Decision JSON ONLY):
{
  "decision": "ACCEPT" | "REJECT",
  "feedback": string | null
}

RULES:
1. If worker_answer is null or missing, set decision = "REJECT" with feedback explaining the missing result.
2. If worker_answer.sentiment == plan.target_sentiment: decision = "ACCEPT" and feedback = null.
3. Otherwise: decision = "REJECT" and feedback must explain the mismatch, e.g., "Expected POSITIVE but got NEGATIVE. Choose a different sentiment in the next plan."
4. Feedback must be actionable so the planner can adjust the next task.
5. Strict JSON only; no extra text.

STATE USAGE:
- You may consider project_state to improve evaluation, but must operate correctly when it is null or missing.
"""


def make_critic(client: OpenAI, model: str) -> Agent[SentimentCriticInput, SentimentCriticOutput]:
    """
    Critic judges the sentiment label for the provided text.
    """
    return Agent(
        name="SentimentCritic",
        client=client,
        model=model,
        system_prompt=PROMPT_CRITIC,
        input_schema=SentimentCriticInput,
        output_schema=SentimentCriticOutput,
        temperature=0.0,
    )
