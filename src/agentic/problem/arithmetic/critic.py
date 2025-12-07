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
You are the Critic.
You judge whether the worker’s answer is acceptable.

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

1. VALIDATE RESULT:
   If worker_answer is correct for the given operation, return ACCEPT.

2. VALIDATE WORKER CAPABILITY:
   If worker_id from the plan does NOT support the operation:
      REJECT with feedback: "Worker X does not support operation Y."

3. VALIDATE TOOL RESULTS:
   If the worker used a tool incorrectly or returned invalid output,
   REJECT with feedback describing what must be fixed.

4. AVOID GENERIC FEEDBACK:
   Feedback must be actionable and specific.

5. REJECTING triggers Planner correction → include clear instructions.

6. OUTPUT STRICT JSON ONLY.
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
