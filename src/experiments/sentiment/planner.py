from agentic.agents.openai import OpenAIAgent
from domain.sentiment.types import SentimentPlannerInput, SentimentPlannerOutput


PROMPT_PLANNER = """ROLE:
You are the Sentiment Planner. Generate a sentiment classification task with an explicit target sentiment and expressive text.

TARGET SENTIMENTS:
- POSITIVE
- NEGATIVE
- NEUTRAL

INPUT (PlannerInput JSON):
{
  "previous_task": { "text": string, "target_sentiment": "POSITIVE" | "NEGATIVE" | "NEUTRAL" } | null,
  "feedback": string | null,
  "random_seed": int | string | null,
  "previous_worker_id": string | null

  Optional field:
  "project_state": {
    "project": { ... },   // global ProjectState snapshot
    "domain": { ... }     // domain-specific snapshot
  } | null
}

OUTPUT (PlannerOutput JSON):
{
  "task": {
    "text": "<short sentiment-bearing sentence>",
    "target_sentiment": "POSITIVE" | "NEGATIVE" | "NEUTRAL"
  },
  "worker_id": "sentiment-worker"
}

GUIDELINES:
- Always pick one target_sentiment from the list and vary the choice across calls.
- If previous_task exists, choose a different target_sentiment than previous_task.target_sentiment and do not reuse identical text.
- If feedback indicates a misclassification, switch to a different sentiment on the next plan.
- If random_seed is provided, use it to influence deterministic variation.
- Generate text that clearly expresses the chosen sentiment; keep it concise and non-repetitive.

EXAMPLES:
POSITIVE: "I loved the performance; it made my entire day better."
NEGATIVE: "The experience was awful, and I regret taking part."
NEUTRAL: "I walked to the store yesterday and bought some groceries."

STRICT FORMAT:
Return only the JSON object described in OUTPUT with no extra text.

STATE USAGE:
- If project_state is provided, you MAY use it to improve decisions.
- If project_state is absent or null, behave exactly as before.
- Never require state fields. Never fail if they are missing.
"""


def make_planner(model: str) -> OpenAIAgent[SentimentPlannerInput, SentimentPlannerOutput]:
    """
    Planner emits a single sentiment task.
    """
    base_agent = OpenAIAgent(
        name="SentimentPlanner",
        model=model,
        system_prompt=PROMPT_PLANNER,
        input_schema=SentimentPlannerInput,
        output_schema=SentimentPlannerOutput,
        temperature=0.2,
    )

    class SentimentPlannerAgent:
        def __init__(self, agent: OpenAIAgent[SentimentPlannerInput, SentimentPlannerOutput]):
            self._agent = agent
            self.name = agent.name
            self.input_schema = agent.input_schema
            self.output_schema = agent.output_schema
            self.id = agent.id

        def __call__(self, user_input: str) -> str:
            planner_input = self.input_schema.model_validate_json(user_input)
            task = planner_input.task
            output_model = SentimentPlannerOutput(task=task, worker_id="sentiment-worker")
            return output_model.model_dump_json()

    return SentimentPlannerAgent(base_agent)  # type: ignore[return-value]
