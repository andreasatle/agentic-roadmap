from openai import OpenAI
from agentic.agents import Agent
from agentic.problem.arithmetic.types import ArithmeticWorkerInput, ArithmeticWorkerOutput

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
Your job is to execute the ArithmeticTask or request a tool to do so.

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

1. DO NOT GUESS worker_id. Only Planner chooses worker_id.

2. TOOL CHOICE:
   For each op:
     ADD → tool_name = "add"
     SUB → tool_name = "sub"
     MUL → tool_name = "mul"

3. CONSISTENCY:
   Use the correct args and field names:
     ADD → {"tool_name": "add", "args": {"a": task.a, "b": task.b}}
     SUB → {"tool_name": "sub", "args": {"a": task.a, "b": task.b}}
     MUL → {"tool_name": "mul", "args": {"a": task.a, "b": task.b}}
   No extra keys (do NOT use x/y or other fields).

4. TOOL RESULT HANDLING:
   If tool_result is NOT null, emit {"result": tool_result} and do NOT request another tool.

5. FEEDBACK HANDLING:
   If feedback exists, correct mistakes from prior iterations.

6. OUTPUT STRICT JSON ONLY.
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
