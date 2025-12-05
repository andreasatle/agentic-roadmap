from openai import OpenAI
from ...agents import Agent
from .types import ArithmeticWorkerInput, ArithmeticWorkerOutput

def make_worker(client: OpenAI, model: str) -> Agent[ArithmeticWorkerInput, ArithmeticWorkerOutput]:
    """
    Worker emits either:
      - a tool_request, or
      - a numeric result.

    It NEVER executes the tool itself.
    """
    worker_prompt = """
ROLE:
You are the Worker.
You may either:
- request a deterministic arithmetic tool, or
- emit a final numeric result.

INPUT (already validated JSON; schema = WorkerInput):
{
  "task": {
    "op": "ADD" | "SUB" | "MUL",
    "a": int,
    "b": int
  },
  "previous_result": { "value": int } | null,
  "feedback": string | null,
  "tool_result": { "value": int } | null
}

OUTPUT CONTRACT (emit EXACTLY ONE of the branches below):

1) Request a tool:
{
  "tool_request": {
    "tool_name": "compute",
    "args": {
      "op": "ADD" | "SUB" | "MUL",
      "a": int,
      "b": int
    }
  }
}

2) Emit numeric result:
{
  "result": {
    "value": int
  }
}

RULES:
- NEVER execute the tool yourself; you only request it.
- On the FIRST turn (tool_result == null), you are encouraged to request the "compute" tool.
- When tool_result is non-null, you should normally emit a numeric result based on it.
- You may use previous_result and feedback to correct prior mistakes, but NEVER include them in output.
- Do NOT include both result and tool_request.
- Do NOT change op/a/b compared to the input task when requesting the tool.
- Output ONLY a valid JSON object matching WorkerOutput schema. No extra text.
"""
    return Agent(
        name="worker",
        client=client,
        model=model,
        system_prompt=worker_prompt,
        input_schema=ArithmeticWorkerInput,
        output_schema=ArithmeticWorkerOutput,
        temperature=0.4,
    )
