from openai import OpenAI

from ...agents import Agent
from .types import SentimentWorkerInput, SentimentWorkerOutput


def make_worker(client: OpenAI, model: str) -> Agent[SentimentWorkerInput, SentimentWorkerOutput]:
    """
    Worker emits a sentiment label (no tools in this domain).
    """
    worker_prompt = """
ROLE:
You are the Sentiment Worker.
Emit a single sentiment label.
Output must be valid JSON only.

INPUT (already validated JSON; schema = WorkerInput):
{
  "task": {
    "text": string
  },
  "previous_result": { "sentiment": string } | null,
  "feedback": string | null,
  "tool_result": { "sentiment": string } | null
}

OUTPUT CONTRACT (emit EXACTLY ONE branch):
{
  "result": {
    "sentiment": "POSITIVE" | "NEGATIVE" | "NEUTRAL"
  }
}

RULES:
- Do NOT include tool_request (this domain has no tools).
- If feedback suggests correction, adjust the sentiment.
- Emit ONLY a valid JSON object matching WorkerOutput schema. No extra text.
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
