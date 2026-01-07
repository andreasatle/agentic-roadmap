from typing import Literal, Union

from pydantic import BaseModel, ConfigDict, model_validator
from agentic_workflow.schemas import Decision, PlannerOutput, WorkerInput, WorkerOutput
from agentic_workflow.agent_dispatcher import AgentDispatcher


class ArithmeticTask(BaseModel):
    """Domain task schema shared by planner/worker/critic."""
    op: Literal["ADD", "SUB", "MUL"]
    a: int
    b: int


class AddArgs(BaseModel):
    a: int
    b: int


class SubArgs(BaseModel):
    a: int
    b: int


class MulArgs(BaseModel):
    a: int
    b: int


class ArithmeticResult(BaseModel):
    value: int


class WorkerSpec(BaseModel):
    worker_id: str
    supported_ops: set[Literal["ADD", "SUB", "MUL"]]


ArithmeticArgs = Union[AddArgs, SubArgs, MulArgs]


WORKER_CAPABILITIES: dict[str, WorkerSpec] = {
    "worker_addsub": WorkerSpec(
        worker_id="worker_addsub",
        supported_ops={"ADD", "SUB"},
    ),
    "worker_mul": WorkerSpec(
        worker_id="worker_mul",
        supported_ops={"MUL"},
    ),
}

ArithmeticToolArgs = AddArgs | SubArgs | MulArgs
TOOL_ARG_BY_NAME = {
    "add": AddArgs,
    "sub": SubArgs,
    "mul": MulArgs,
}

# Bind generics to domain
class ArithmeticPlannerInput(BaseModel):
    model_config = ConfigDict(extra="allow")

    task: ArithmeticTask

ArithmeticPlannerOutput = PlannerOutput[ArithmeticTask]
ArithmeticWorkerInput = WorkerInput[ArithmeticTask, ArithmeticResult]


class ArithmeticWorkerOutput(WorkerOutput[ArithmeticResult]):
    @model_validator(mode="after")
    def coerce_tool_args(self) -> "ArithmeticWorkerOutput":
        if self.tool_request is None:
            return self

        target_type = TOOL_ARG_BY_NAME.get(self.tool_request.tool_name)
        if target_type is None:
            return self

        if isinstance(self.tool_request.args, target_type):
            return self

        self.tool_request.args = target_type.model_validate(self.tool_request.args)
        return self


class ArithmeticCriticInput(BaseModel):
    model_config = ConfigDict(extra="allow")

    plan: ArithmeticTask
    worker_id: str
    worker_answer: ArithmeticResult | None

    def to_llm(self) -> dict:
        raw = self.model_dump()
        normalized = _normalize_for_json(raw)
        return normalized


ArithmeticCriticOutput = Decision

class ArithmeticDispatcher(AgentDispatcher[ArithmeticTask, ArithmeticResult, Decision]):
    pass
