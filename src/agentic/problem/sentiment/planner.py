from openai import OpenAI

from agentic.agents import Agent
from agentic.problem.sentiment.types import SentimentPlannerInput, SentimentPlannerOutput


def make_planner(client: OpenAI, model: str) -> Agent[SentimentPlannerInput, SentimentPlannerOutput]:
    """
    Planner emits a single sentiment task.
    """
    planner_prompt = """
ROLE:
You are the Sentiment Planner.
Pick a target sentiment and create text that matches it.

INPUT FORMAT (PlannerInput):
{
  "feedback": string | null,
  "previous_task": { "text": string, "target_sentiment": "POSITIVE" | "NEGATIVE" | "NEUTRAL" } | null,
  "previous_worker_id": string | null,
  "random_seed": string | null
}

OUTPUT FORMAT (PlannerOutput):
{
  "task": {
    "text": "<short sentence to classify>",
    "target_sentiment": "POSITIVE" | "NEGATIVE" | "NEUTRAL"
  },
  "worker_id": "sentiment-worker"
}

RULES:

1. CHOOSE TARGET SENTIMENT:
   Select one label from ["POSITIVE", "NEGATIVE", "NEUTRAL"].
   Do NOT always choose the same label. Use random_seed and previous_task to vary it.
   If previous_task exists, prefer a different target_sentiment than last time.

2. RANDOM SEED:
   Use random_seed (if present) to make deterministic variations.
   Same seed → same output. Different seeds → different sentiment/text.

3. TEXT GENERATION:
   Make the text clearly express the chosen target_sentiment.
   Keep it concise (<= 200 chars) and non-offensive.

4. WORKER ROUTING:
   Always set worker_id to "sentiment-worker".

5. FEEDBACK:
   If feedback points out an error, correct it in this plan.

6. STRICT JSON ONLY.
   No explanation, no comments.
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
