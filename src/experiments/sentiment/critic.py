from agentic.agents.openai import OpenAIAgent
from domain.sentiment.types import SentimentCriticInput, SentimentCriticOutput


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
  "feedback": null | {
    "kind": "EMPTY_RESULT" | "MISMATCH" | "OTHER",
    "message": string
  }
}

RULES:
1. If worker_answer is null or missing, set decision = "REJECT" with feedback.kind="EMPTY_RESULT" and a short message.
2. If worker_answer.sentiment == plan.target_sentiment: decision = "ACCEPT" and feedback = null.
3. Otherwise: decision = "REJECT" with feedback.kind="MISMATCH" and feedback.message explaining the expected vs. actual sentiment so the planner can adjust.
4. Feedback must be actionable so the planner can adjust the next task. Strict JSON only; no extra text.

STATE USAGE:
- You may consider project_state to improve evaluation, but must operate correctly when it is null or missing.
"""


def make_critic(model: str) -> OpenAIAgent[SentimentCriticInput, SentimentCriticOutput]:
    """
    Critic judges the sentiment label for the provided text.
    """
    return OpenAIAgent(
        name="SentimentCritic",
        model=model,
        system_prompt=PROMPT_CRITIC,
        input_schema=SentimentCriticInput,
        output_schema=SentimentCriticOutput,
        temperature=0.0,
    )
