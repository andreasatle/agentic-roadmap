from openai import OpenAI

from agentic.agents import Agent
from agentic.problem.coder.types import CoderWorkerInput, CoderWorkerOutput


def make_worker(client: OpenAI, model: str) -> Agent[CoderWorkerInput, CoderWorkerOutput]:
    """
    Worker produces code that satisfies the coding task.
    """
    worker_prompt = """
ROLE:
You are the Coder Worker. Produce code that satisfies the task specification and requirements.

INPUT (WorkerInput JSON):
{
  "task": {
    "language": "python" | "javascript",
    "specification": string,
    "requirements": [string, ...]
  },
  "previous_result": { "code": string } | null,
  "feedback": string | null,
  "tool_result": null
}

OUTPUT (exactly one branch):
{
  "result": { "code": "<code in the requested language>" }
}

RULES:
- Write code in task.language only.
- Address every requirement explicitly; keep code minimal and runnable without external dependencies.
- No tool_request field; tools are not available.
- Use feedback to fix prior issues.
- Strict JSON only; no commentary outside the JSON.
"""
    return Agent(
        name="coder-worker",
        client=client,
        model=model,
        system_prompt=worker_prompt,
        input_schema=CoderWorkerInput,
        output_schema=CoderWorkerOutput,
        temperature=0.2,
    )
