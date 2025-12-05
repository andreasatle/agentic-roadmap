"""
Iteration 6 – Agents with supervisor-controlled tools.

Key differences from Iteration 5b:
- Agents NEVER execute tools.
- Worker only EMITS tool_request/result JSON; Supervisor owns tool execution.
- No OpenAI tools API usage here -> vendor-neutral contracts.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic
from openai import OpenAI

from .protocols import InputSchema, OutputSchema
from .schemas import (
    PlannerInput,
    PlannerOutput,
    WorkerInput,
    WorkerOutput,
    CriticInput,
    CriticOutput,
)


# ============================================================
# Generic Agent Wrapper
# ============================================================

@dataclass
class Agent(Generic[InputSchema, OutputSchema]):
    """
    Generic LLM-based agent.

    The Supervisor is the trusted layer. Agents are untrusted.
    Their only job is:
        input_json  -> LLM -> validated_output_json
    """
    name: str
    client: OpenAI
    model: str
    system_prompt: str
    input_schema: type[InputSchema]
    output_schema: type[OutputSchema]
    temperature: float = 0.0

    def __call__(self, user_input: str) -> str:
        """
        user_input is already JSON (input_schema.model_dump_json()).
        We always enforce json_object output.
        """
        resp = self.client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": self.system_prompt.strip()},
                {"role": "user", "content": user_input},
            ],
        )
        message = resp.choices[0].message
        return (message.content or "").strip()


# ============================================================
# Agent Constructors
# ============================================================

def make_planner(client: OpenAI, model: str) -> Agent[PlannerInput, PlannerOutput]:
    """
    Planner emits a single Task.
    Must match PlannerOutput == Task schema.
    """
    planner_prompt = """
ROLE:
You are the Planner.
Emit a single arithmetic Task.

INPUT:
- You are called with an empty JSON object: {}.

OUTPUT (JSON ONLY, NO TEXT AROUND IT):
{
  "op": "ADD" | "SUB" | "MUL",
  "a": <int>,
  "b": <int>
}

RULES:
- Choose op uniformly from {"ADD","SUB","MUL"}.
- Choose a and b uniformly from [1, 20].
- Emit ONLY valid JSON matching the Task schema.
- No comments, no trailing commas, no extra fields.
"""
    return Agent(
        name="Planner",
        client=client,
        model=model,
        system_prompt=planner_prompt,
        input_schema=PlannerInput,
        output_schema=PlannerOutput,
        temperature=0.4,
    )


def make_worker(client: OpenAI, model: str) -> Agent[WorkerInput, WorkerOutput]:
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
        name="Worker",
        client=client,
        model=model,
        system_prompt=worker_prompt,
        input_schema=WorkerInput,
        output_schema=WorkerOutput,
        temperature=0.0,
    )


def make_critic(client: OpenAI, model: str) -> Agent[CriticInput, CriticOutput]:
    """
    Critic recomputes the Task and judges Worker’s result.value for correctness.
    Emits a single Decision object (ACCEPT/REJECT).
    """
    critic_prompt = """
ROLE:
You are the Critic.
Evaluate the Worker's numeric result for correctness.

INPUT (JSON; schema = CriticInput):
{
  "plan": {
    "op": "ADD" | "SUB" | "MUL",
    "a": int,
    "b": int
  },
  "worker_answer": {
    "value": int
  }
}

OUTPUT CONTRACT (JSON ONLY):
{
  "decision": "ACCEPT" | "REJECT",
  "feedback": string | null
}

RULES:
- Compute the correct result from plan.op(plan.a, plan.b).
- Compare it to worker_answer.value.
- If correct:
    {"decision": "ACCEPT", "feedback": "correct"}
- If incorrect:
    {"decision": "REJECT",
     "feedback": "expected <CORRECT> but got <Z>"}
- When decision == "REJECT", feedback MUST be a non-empty string.
- Emit ONLY valid JSON matching the Decision schema. No text outside the object.
"""
    return Agent(
        name="Critic",
        client=client,
        model=model,
        system_prompt=critic_prompt,
        input_schema=CriticInput,
        output_schema=CriticOutput,
        temperature=0.0,
    )
