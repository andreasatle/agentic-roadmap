"""
Iteration 3 agents.

Same roles as Iteration 2, but:
- We set role-appropriate temperatures.
- We force JSON output via response_format=json_object.
- Prompts are TEMPLATE + invariants only.

Agents remain dumb and narrow.
All robustness lives in the Supervisor.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar
from openai import OpenAI

# Your new protocol uses these:
from .protocols import AgentInput, AgentOutput  # Input, Output = TypeVar(...)

# Concrete schemas
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


@dataclass
class Agent(Generic[InputSchema, OutputSchema]):
    """
    Generic LLM-based agent.

    - Takes a string (serialized InputSchema)
    - Returns a string (serialized OutputSchema)
    - Supervisor is responsible for all validation and retries
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
            response_format={"type": "json_object"},  # JSON-only mode
            messages=[
                {"role": "system", "content": self.system_prompt.strip()},
                {"role": "user", "content": user_input},
            ],
        )
        return resp.choices[0].message.content.strip()


def make_planner(client: OpenAI, model: str) -> Agent[PlannerInput, PlannerOutput]:
    planner_prompt = """
ROLE:
You are the Planner.
Your task is to generate a simple arithmetic task.

INPUT FORMAT:
""

OUTPUT FORMAT TEMPLATE:
{"op": "$OP", "a": $A, "b": $B}

INVARIANTS:
- Replace placeholders with real JSON values.
- $OP ∈ {"ADD", "SUB", "MUL"} chosen uniformly at random.
- $A and $B are integers between 1 and 20 chosen uniformly at random.
- Output ONLY valid JSON.
- No explanation, no extra text, no comments, no trailing commas.
"""
    return Agent(
        name="Planner",
        client=client,
        model=model, 
        system_prompt=planner_prompt, 
        input_schema=PlannerInput, 
        output_schema=PlannerOutput, 
        temperature=0.4
    )


def make_worker(client: OpenAI, model: str) -> Agent[WorkerInput, WorkerOutput]:
    worker_prompt = """
ROLE:
You are the Worker.
You MUST compute the arithmetic EXACTLY and return the correct result.
This is a strict correctness test. No mistakes are allowed.

INPUT FORMAT TEMPLATE:
{"op": "$OP", "a": $A, "b": $B}

OUTPUT FORMAT TEMPLATE:
{"result": $Z}

INVARIANTS:
- The result must be mathematically correct. Incorrect results will be rejected.
- Replace placeholders with real JSON values.
- $Z must be an integer.
- Output ONLY valid JSON.
- No explanation, no extra text, no comments.
"""
    return Agent(
        name="Worker",
        client=client,
        model=model, 
        system_prompt=worker_prompt, 
        input_schema=WorkerInput, 
        output_schema=WorkerOutput, 
        temperature=0.0
    )


def make_critic(client: OpenAI, model: str) -> Agent[CriticInput, CriticOutput]:
    critic_prompt = """
ROLE:
You are the Critic.
Verify correctness.

INPUT FORMAT TEMPLATE:
{"op": "$OP", "a": $A, "b": $B, "result": $Z}

OUTPUT FORMAT TEMPLATE:
{"decision": "ACCEPT"} OR {"decision": "REJECT"}

INVARIANTS:
- Output ONLY valid JSON.
- decision ∈ {"ACCEPT","REJECT"}.
- No explanation, no extra fields, no comments.
"""
    return Agent(
        name="Critic",
        client=client, 
        model=model, 
        system_prompt=critic_prompt, 
        input_schema=CriticInput, 
        output_schema=CriticOutput, 
        temperature=0.0
    )
