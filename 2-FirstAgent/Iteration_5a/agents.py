from __future__ import annotations
from dataclasses import dataclass
from typing import TypeVar, Generic
from openai import OpenAI

from .schemas import PlannerInput, PlannerOutput, WorkerInput, WorkerOutput, CriticInput, CriticOutput

InputSchema = TypeVar("InputSchema", bound=PlannerInput | WorkerInput | CriticInput)
OutputSchema = TypeVar("OutputSchema", bound=WorkerOutput | WorkerOutput | CriticOutput)


# ============================================================
# Generic Agent Wrapper
# ============================================================

@dataclass
class Agent(Generic[InputSchema, OutputSchema]):
    """
    Generic LLM-based agent.
    Agents are untrusted. Supervisor performs all validation.
    Contract:
        input_json -> LLM -> validated_output_json
    """
    name: str
    client: OpenAI
    model: str
    system_prompt: str
    input_schema: type[InputSchema]
    output_schema: type[OutputSchema]
    temperature: float = 0.0

    def __call__(self, input_json: str) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": self.system_prompt.strip()},
                {"role": "user",   "content": input_json},
            ],
        )
        return resp.choices[0].message.content.strip()


# ============================================================
# Agent Constructors
# ============================================================

def make_planner(client: OpenAI, model: str) -> Agent[PlannerInput, PlannerOutput]:
    """
    Planner emits a single Task.
    Must match output schema: Task (alias for arithmetic task).
    """
    planner_prompt = """
ROLE:
You are the Planner.
Emit a single arithmetic Task.

INPUT CONTRACT:
""

OUTPUT TEMPLATE (JSON; replace placeholders):
{"op":"<ADD|SUB|MUL>","a":<INT>,"b":<INT>}

RULES:
- Choose op uniformly from {"ADD","SUB","MUL"}.
- Choose a and b uniformly from [1,20].
- Emit ONLY valid JSON matching Task schema.
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
    Worker emits either a numeric result OR a tool request.
    Must match WorkerOutput schema exactly.
    """
    worker_prompt = """
ROLE:
You are the Worker.
Delegate arithmetic to the compute tool, then emit the numeric result on retry.

INPUT TEMPLATE (JSON; replace placeholders):
{"task":{"op":"<ADD|SUB|MUL>","a":<INT>,"b":<INT>},"previous_result":null,"feedback":null,"tool_result":null}

OUTPUT CONTRACT (emit exactly one, top-level):

Tool request branch:
   {"tool_request":{"tool_name":"compute","task":{"op":"<ADD|SUB|MUL>","a":<INT>,"b":<INT>}}}

Numeric result branch (only after receiving tool_result):
   {"result":{"value":<INT>}}

RULES:
- First turn ALWAYS emit the tool_request branch.
- On retry (after tool execution), emit ONLY the result branch with result.value = tool_result.value.
- Never emit both branches.
- Never include previous_result, feedback, or tool_result in output.
- Never change op/a/b from the provided task.
- Emit ONLY valid JSON matching the schema. No text outside the object.
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
    Critic recomputes Task and judges Worker’s result.value for correctness.
    Emits a single Decision object (ACCEPT/REJECT).
    """
    critic_prompt = """
ROLE:
You are the Critic.
Evaluate Worker’s numeric Result for correctness.

INPUT TEMPLATE (JSON; replace placeholders):
{"plan":{"op":"<ADD|SUB|MUL>","a":<INT>,"b":<INT>},"worker_answer":{"value":<INT>}}

OUTPUT CONTRACT (top-level):
{"decision":"ACCEPT","feedback":"correct"}
or
{"decision":"REJECT","feedback":"expected <CORRECT> but got <Z>"}

RULES:
- Recompute the correct result yourself from plan.
- Compare with worker_answer.value.
- If REJECT, feedback must be non-empty.
- Emit ONLY valid JSON. No text outside the object.
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
