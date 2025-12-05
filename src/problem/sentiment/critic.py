from openai import OpenAI

from ...agents import Agent
from .types import SentimentCriticInput, SentimentCriticOutput


def make_critic(client: OpenAI, model: str) -> Agent[SentimentCriticInput, SentimentCriticOutput]:
    """
    Critic judges the sentiment label for the provided text.
    """
    critic_prompt = """
ROLE:
You are the Sentiment Critic.
Evaluate whether the Worker produced a reasonable sentiment label.
Output must be valid JSON only.

INPUT (JSON; schema = CriticInput):
{
  "plan": {
    "text": string
  },
  "worker_answer": {
    "sentiment": "POSITIVE" | "NEGATIVE" | "NEUTRAL"
  }
}

OUTPUT CONTRACT (JSON ONLY):
{
  "decision": "ACCEPT" | "REJECT",
  "feedback": string | null
}

RULES:
- Assess whether the sentiment label fits the text.
- If acceptable:
    {"decision": "ACCEPT", "feedback": "looks correct"}
- If not:
    {"decision": "REJECT",
     "feedback": "expected <SENTIMENT> because <SHORT REASON>"}
- When decision == "REJECT", feedback MUST be a non-empty string.
- Emit ONLY valid JSON matching the Decision schema. No text outside the object.
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
