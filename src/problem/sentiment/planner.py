from openai import OpenAI

from ...agents import Agent
from .types import SentimentPlannerInput, SentimentPlannerOutput


def make_planner(client: OpenAI, model: str) -> Agent[SentimentPlannerInput, SentimentPlannerOutput]:
    """
    Planner emits a single sentiment task.
    """
    planner_prompt = """
ROLE:
You are the Sentiment Planner.
Emit a single sentiment analysis task.
Output must be valid JSON only.

INPUT:
- You are called with an empty JSON object: {}.

OUTPUT (JSON ONLY, NO TEXT AROUND IT):
{
  "task": {
    "text": "<short sentence to classify>"
  }
}

RULES:
- Provide a concise sentence (<= 200 chars).
- Avoid offensive content.
- Emit ONLY valid JSON matching the Task schema.
- No comments, no trailing commas, no extra fields.
"""
    return Agent(
        name="SentimentPlanner",
        client=client,
        model=model,
        system_prompt=planner_prompt,
        input_schema=SentimentPlannerInput,
        output_schema=SentimentPlannerOutput,
        temperature=0.2,
    )
