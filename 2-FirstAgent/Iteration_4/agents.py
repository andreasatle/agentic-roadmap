"""
Iteration 4 agents.

Changes from Iteration 3:
- Worker now receives previous_result + feedback.
- Critic always returns decision + optional feedback.
- Prompts explicitly mention all inputs.
- All responses enforced as JSON via response_format=json_object.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar
from openai import OpenAI

from .protocols import AgentInput, AgentOutput
from .schemas import (
    PlannerInput,
    PlannerOutput,
    WorkerInput,
    WorkerOutput,
    CriticInput,
    CriticOutput,
)

InputSchema = TypeVar("InputSchema", bound=AgentInput)
OutputSchema = TypeVar("OutputSchema", bound=AgentOutput)


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
        resp = self.client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": self.system_prompt.strip()},
                {"role": "user",   "content": user_input},
            ],
        )
        return resp.choices[0].message.content.strip()


# ============================================================
# Agent Constructors
# ============================================================

def make_planner(client: OpenAI, model: str) -> Agent[PlannerInput, PlannerOutput]:
    planner_prompt = """
ROLE:
You are the Planner.
Generate a simple arithmetic task in JSON.

INPUT FORMAT:
""

OUTPUT FORMAT TEMPLATE:
{"op": "$OP", "a": $A, "b": $B}

INVARIANTS:
- $OP ∈ {"ADD","SUB","MUL"} chosen uniformly.
- $A and $B integers ∈ [1, 20].
- Replace all placeholders.
- Output ONLY valid JSON.
- No text, no comments, no trailing commas.
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
    worker_prompt = """
ROLE:
You are the Worker.
Compute the correct result for the arithmetic operation.

INPUT FORMAT:
{
  "op": "...",
  "a": X,
  "b": Y,
  "previous_result": P,
  "feedback": F
}

OUTPUT FORMAT:
{"result": Z}

RULES:
- Z must be the correct result of applying op to a and b.
- previous_result may be null or incorrect.
- feedback may be null or a hint from the Critic.
- Use previous_result and feedback to fix earlier mistakes if any.
- Output ONLY valid JSON.
- No explanation, no extra fields.
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
    critic_prompt = """
ROLE:
You are the Critic.
Check whether Worker's result Z is correct.

INPUT FORMAT:
{"op": "...", "a": X, "b": Y, "result": Z}

OUTPUT FORMAT:
{
  "decision": "ACCEPT" | "REJECT",
  "feedback": "string or null"
}

RULES:
- Compute the correct result yourself.
- If Z is correct:
      {"decision": "ACCEPT", "feedback": "correct"}
- If Z is incorrect:
      {"decision": "REJECT",
       "feedback": "expected <CORRECT> but got <Z>"}
- Output ONLY valid JSON.
- No explanation outside the JSON object.
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
