from __future__ import annotations
import json
from dataclasses import dataclass
from typing import Any, Callable, Generic, Mapping, TypeVar
from openai import OpenAI
from openai.types.chat import ChatCompletionMessage

from .schemas import PlannerInput, PlannerOutput, WorkerInput, WorkerOutput, CriticInput, CriticOutput, Task
from .tools import make_tool_from_schema
from .compute import compute

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
    tools: list[dict[str, Any]] | None = None
    tool_functions: Mapping[str, Callable[..., Any]] | None = None

    def __call__(self, input_json: str) -> str:
        messages = [
            {"role": "system", "content": self.system_prompt.strip()},
            {"role": "user", "content": input_json},
        ]

        message = self._call_llm(messages, use_tools=True)

        if message.tool_calls:
            messages = self._handle_tool_calls(message, messages)
            message = self._call_llm(messages, use_tools=False)

        return (message.content or "").strip()

    def _get_agent_args(self, messages: list[dict[str, Any]], use_tools: bool = True) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "temperature": self.temperature,
            "messages": messages,
        }
        if use_tools and self.tools:
            kwargs["tools"] = self.tools
            kwargs["tool_choice"] = "required"
        else:
            kwargs["response_format"] = {"type": "json_object"}
        return kwargs

    def _call_llm(self, messages: list[dict[str, Any]], use_tools: bool) -> ChatCompletionMessage:
        kwargs = self._get_agent_args(messages, use_tools=use_tools)
        resp = self.client.chat.completions.create(**kwargs)
        return resp.choices[0].message

    def _handle_tool_calls(
        self,
        message: ChatCompletionMessage,
        messages: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if not self.tool_functions:
            raise RuntimeError("Tool call requested but no tool_functions registered.")

        messages.append(
            {
                "role": "assistant",
                "content": message.content or "",
                "tool_calls": message.tool_calls,
            }
        )
        for call in message.tool_calls:
            tool_name = call.function.name
            tool_fn = self.tool_functions.get(tool_name)
            if tool_fn is None:
                raise RuntimeError(f"Unknown tool requested: {tool_name}")

            args = json.loads(call.function.arguments or "{}")
            tool_output = tool_fn(**args)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "name": tool_name,
                    "content": json.dumps({"value": tool_output}),
                }
            )

        return messages


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
Call the provided compute tool to perform arithmetic, then emit the numeric result.

INPUT TEMPLATE (JSON; replace placeholders):
{"task":{"op":"<ADD|SUB|MUL>","a":<INT>,"b":<INT>},"previous_result":null,"feedback":null,"tool_result":null}

RULES:
- First respond by calling the compute tool with exactly the provided op/a/b.
- Never compute inside the LLM; always rely on the tool call.
- After the tool result is provided, reply with ONLY: {"result":{"value":<INT>}}.
- Never alter op/a/b from the provided task.
- Emit ONLY valid JSON matching the schema. No text outside the object.
"""

    compute_tool = make_tool_from_schema(
        name="compute",
        description="Deterministic arithmetic over two integers.",
        schema_model=Task,
    )

    return Agent(
        name="Worker",
        client=client,
        model=model,
        system_prompt=worker_prompt,
        input_schema=WorkerInput,
        output_schema=WorkerOutput,
        temperature=0.0,
        tools=[compute_tool],
        tool_functions={"compute": compute},
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
