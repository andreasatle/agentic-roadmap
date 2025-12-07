from openai import OpenAI
from agentic.agents import Agent
from agentic.problem.arithmetic.types import ArithmeticCriticInput, ArithmeticCriticOutput, WORKER_CAPABILITIES


def make_critic(client: OpenAI, model: str) -> Agent[ArithmeticCriticInput, ArithmeticCriticOutput]:
    worker_specs = "\n".join(
        f"- {worker_id}: supports {', '.join(sorted(spec.supported_ops))}"
        for worker_id, spec in sorted(WORKER_CAPABILITIES.items())
    )
    prompt = """
ROLE:
You are the Arithmetic Critic.
Enforce correctness and proper worker routing.

Capability table:
- worker_addsub → supports ["ADD", "SUB"]
- worker_mul → supports ["MUL"]

INPUT (CriticInput):
{
  "plan": ArithmeticTask,
  "worker_answer": ArithmeticResult | null
}

OUTPUT (CriticOutput):
{"decision": "ACCEPT"}
or
{"decision": "REJECT", "feedback": "reason"}

RULES:
1. Validate worker compatibility:
   - If plan.op not in the worker’s capability set → REJECT, e.g., "Wrong worker selected for MUL. Expected worker_mul."
2. Validate result correctness:
   - Compute expected = op(a, b). If worker_answer is null or incorrect → REJECT with specific math feedback.
3. Unsupported operation handling:
   - If the worker attempted an op outside its capability → REJECT with guidance to reroute.
4. Tool usage:
   - If the operation required a tool but the worker failed to use it correctly → REJECT with actionable feedback.
5. Accept only when BOTH the worker routing is correct AND the result matches expected.
6. Feedback must be actionable; Strict JSON only.
"""

    return Agent(
        name="Critic",
        client=client,
        model=model,
        system_prompt=prompt,
        input_schema=ArithmeticCriticInput,
        output_schema=ArithmeticCriticOutput,
        temperature=0.0,
    )
