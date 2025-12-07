from openai import OpenAI

from agentic.agents import Agent
from agentic.problem.sentiment.types import SentimentWorkerInput, SentimentWorkerOutput


def make_worker(client: OpenAI, model: str) -> Agent[SentimentWorkerInput, SentimentWorkerOutput]:
    """
    Worker emits a sentiment label (no tools in this domain).
    """
    worker_prompt = """
ROLE:
You are the Sentiment Worker.
Classify the sentiment of the provided text.

INPUT (WorkerInput JSON):
{
  "task": { "text": string, "target_sentiment": "POSITIVE" | "NEGATIVE" | "NEUTRAL" },
  "previous_result": { "sentiment": string } | null,
  "feedback": string | null,
  "tool_result": null
}

OUTPUT (emit EXACTLY ONE branch):
{
  "result": {
    "sentiment": "POSITIVE" | "NEGATIVE" | "NEUTRAL"
  }
}

RULES:
- Ignore task.target_sentiment when classifying; decide based on the text only.
- Positive/praising text → POSITIVE.
- Negative/complaining/disappointed text → NEGATIVE.
- Factual or balanced text → NEUTRAL.
- Do NOT include tool_request (no tools exist here).
- Use feedback to correct prior mistakes.
- Strict JSON only; no extra text.
"""
    return Agent(
        name="SentimentWorker",
        client=client,
        model=model,
        system_prompt=worker_prompt,
        input_schema=SentimentWorkerInput,
        output_schema=SentimentWorkerOutput,
        temperature=0.0,
    )
