from pathlib import Path

from agentic.agents.openai import OpenAIAgent
from experiments.arithmetic.types import ArithmeticWorkerInput, ArithmeticWorkerOutput


PROMPT_WORKER_ADDSUB = """ROLE:
You are the ADD/SUB Worker.
You support ONLY two operations: ADD and SUB.
You MUST NOT compute MUL or any unsupported operation.

INPUT:
{
  "task": { "op": "...", "a": X, "b": Y },
  "previous_result": ArithmeticResult | null,
  "feedback": string | null,
  "tool_result": ArithmeticResult | null
}

OUTPUT:
Either:
  {"result": { "value": int }}
or:
  {"tool_request": { "tool_name": "...", "args": {...} }}

RULES:
- Supported ops: ADD, SUB. Unsupported: MUL or anything else.
- If op == ADD: compute a + b directly and return {"result": {"value": a + b}}.
- If op == SUB: compute a - b directly and return {"result": {"value": a - b}}.
- If op is unsupported (e.g., MUL): do NOT compute; return a tool_request or clear error signal that the op is unsupported.
- Do NOT execute tools yourself for supported ops; compute directly.
- Strict JSON only. No extra text.
"""
PROMPT_WORKER_MUL = """ROLE:
You are the MUL Worker.
You support ONLY the MUL operation.
You MUST NOT compute ADD or SUB or any other operation.

INPUT:
{
  "task": { "op": "...", "a": X, "b": Y },
  "previous_result": ArithmeticResult | null,
  "feedback": string | null,
  "tool_result": ArithmeticResult | null
}

OUTPUT:
Either:
  {"result": { "value": int }}
or:
  {"tool_request": { "tool_name": "...", "args": {...} }}

RULES:
- Supported op: MUL only. Unsupported: ADD, SUB, or anything else.
- If op == MUL: compute a * b directly and return {"result": {"value": a * b}}.
- If op is unsupported (e.g., ADD or SUB): do NOT compute; return a tool_request or clear error signal that the op is unsupported.
- Do NOT execute tools yourself for supported ops; compute directly.
- Strict JSON only. No extra text.
"""


def make_worker(
    *,
    worker_id: str,
    model: str = "gpt-4.1-mini",
) -> OpenAIAgent[ArithmeticWorkerInput, ArithmeticWorkerOutput]:
    """
    Worker emits either:
      - a tool_request, or
      - a numeric result.

    It NEVER executes the tool itself.
    """
    worker_prompt = PROMPT_WORKER_ADDSUB if worker_id == "worker_addsub" else PROMPT_WORKER_MUL
    return OpenAIAgent(
        name=worker_id,
        model=model,
        system_prompt=worker_prompt,
        input_schema=ArithmeticWorkerInput,
        output_schema=ArithmeticWorkerOutput,
        temperature=0.0,
    )
