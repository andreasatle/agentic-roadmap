from agentic.agents.openai import OpenAIAgent
from domain.sentiment.types import SentimentWorkerInput, SentimentWorkerOutput


PROMPT_WORKER = """ROLE:
You are the Sentiment Worker. Classify the sentiment of task.text.

SENTIMENT CUES:
- POSITIVE: joy, praise, happiness.
- NEGATIVE: anger, disappointment, criticism.
- NEUTRAL: factual, balanced, or emotionless statements.

INPUT (WorkerInput JSON):
{
  "task": { "text": string, "target_sentiment": "POSITIVE" | "NEGATIVE" | "NEUTRAL" },
  "previous_result": { "sentiment": "POSITIVE" | "NEGATIVE" | "NEUTRAL" } | null,
  "feedback": string | null,
  "tool_result": null
}

OUTPUT (exactly one branch):
{
  "result": { "sentiment": "POSITIVE" | "NEGATIVE" | "NEUTRAL" }
}

RULES:
- Look only at task.text when classifying; ignore task.target_sentiment entirely.
- No tool_request field; tools do not exist here.
- Use feedback to correct prior mistakes.
- Strict JSON only; no extra text or analysis.
"""


def make_worker(model: str) -> OpenAIAgent[SentimentWorkerInput, SentimentWorkerOutput]:
    """
    Worker emits a sentiment label (no tools in this domain).
    """
    return OpenAIAgent(
        name="SentimentWorker",
        model=model,
        system_prompt=PROMPT_WORKER,
        input_schema=SentimentWorkerInput,
        output_schema=SentimentWorkerOutput,
        temperature=0.0,
    )
