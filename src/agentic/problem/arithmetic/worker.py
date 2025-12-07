from openai import OpenAI
from agentic.agents import Agent
from agentic.problem.arithmetic.types import ArithmeticWorkerInput, ArithmeticWorkerOutput


def _addsub_prompt() -> str:
    return """
ROLE:
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


def _mul_prompt() -> str:
    return """
ROLE:
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


def make_worker(client: OpenAI, model: str, worker_id: str) -> Agent[ArithmeticWorkerInput, ArithmeticWorkerOutput]:
    """
    Worker emits either:
      - a tool_request, or
      - a numeric result.

    It NEVER executes the tool itself.
    """
    worker_prompt = _addsub_prompt() if worker_id == "worker_addsub" else _mul_prompt()
    return Agent(
        name=worker_id,
        client=client,
        model=model,
        system_prompt=worker_prompt,
        input_schema=ArithmeticWorkerInput,
        output_schema=ArithmeticWorkerOutput,
        temperature=0.4,
    )
