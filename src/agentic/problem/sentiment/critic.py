from openai import OpenAI

from agentic.agents import Agent
from agentic.problem.sentiment.types import SentimentCriticInput, SentimentCriticOutput


def make_critic(client: OpenAI, model: str) -> Agent[SentimentCriticInput, SentimentCriticOutput]:
    """
    Critic judges the sentiment label for the provided text.
    """
    critic_prompt = """
ROLE:
You are the Sentiment Critic.
Evaluate whether the Worker produced a reasonable sentiment label.
Output must be valid JSON only.

INPUT (CriticInput JSON):
{
  "plan": { "text": string, "target_sentiment": "POSITIVE" | "NEGATIVE" | "NEUTRAL" },
  "worker_answer": { "sentiment": "POSITIVE" | "NEGATIVE" | "NEUTRAL" } | null
}

OUTPUT (Decision JSON ONLY):
{"decision": "ACCEPT"}
or
{"decision": "REJECT", "feedback": "reason"}

RULES:
- If worker_answer is missing or null, REJECT with actionable feedback.
- If worker_answer.sentiment == plan.target_sentiment, ACCEPT.
- Otherwise REJECT with concise, specific feedback, e.g., "Expected POSITIVE but got NEGATIVE".
- Feedback must be non-empty on REJECT so the planner can adjust.
- Strict JSON only; no extra text.
"""
    return Agent(
        name="SentimentCritic",
        client=client,
        model=model,
        system_prompt=critic_prompt,
        input_schema=SentimentCriticInput,
        output_schema=SentimentCriticOutput,
        temperature=0.0,
    )
