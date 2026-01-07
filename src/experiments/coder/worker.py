from agentic_workflow.agents.openai import OpenAIAgent
from experiments.coder.types import CoderWorkerInput, CoderWorkerOutput


PROMPT_WORKER = """ROLE:
You are the Coder Worker. Implement the provided subtask exactly as specified.

INPUT (WorkerInput JSON):
{
  "task": {
    "language": "python" | "javascript",
    "specification": string,          // subtask from the project
    "requirements": [string, ...]     // acceptance criteria to satisfy
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
- Implement exactly the task.specification; do not add unrelated features.
- Satisfy EVERY requirement; keep code minimal, self-contained, and dependency-free.
- Use feedback to correct missed requirements or language mismatches.
- No tool_request branch; tools are not available.
- Strict JSON only; no commentary outside the JSON.
"""


def make_worker(model: str) -> OpenAIAgent[CoderWorkerInput, CoderWorkerOutput]:
    """
    Worker produces code that satisfies the coding task.
    """
    return OpenAIAgent(
        name="coder-worker",
        model=model,
        system_prompt=PROMPT_WORKER,
        input_schema=CoderWorkerInput,
        output_schema=CoderWorkerOutput,
        temperature=0.2,
    )
