from pydantic import model_validator
from agentic.schemas import (
    Decision,
    ArithmeticTask,
    ArithmeticResult,
    AddArgs,
    SubArgs,
    MulArgs,
    WorkerSpec,
    PlannerInput,
    PlannerOutput,
    WorkerInput,
    WorkerOutput,
    CriticInput,
)
from agentic.agent_dispatcher import AgentDispatcher


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
ArithmeticPlannerInput = PlannerInput[ArithmeticTask, ArithmeticResult]
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


class ArithmeticCriticInput(CriticInput[ArithmeticTask, ArithmeticResult]):
    worker_id: str
    worker_answer: ArithmeticResult | None = None


ArithmeticCriticOutput = Decision

# Dispatcher binding for this domain
ArithmeticDispatcher = AgentDispatcher[ArithmeticTask, ArithmeticResult, Decision]
