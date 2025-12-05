from dataclasses import dataclass
from typing import Generic, TypeVar

from .schemas import (
    PlannerInput,
    PlannerOutput,
    WorkerInput,
    WorkerOutput,
    CriticInput,
)
from .protocols import AgentProtocol, InputSchema, OutputSchema
from pydantic import ValidationError
from .logging_config import get_logger

logger = get_logger("agentic.dispatcher")

# Domain type parameters
T = TypeVar("T")  # Task
R = TypeVar("R")  # Result
D = TypeVar("D")  # Decision


@dataclass(kw_only=True)
class AgentDispatcherBase:
    """Shared retry/validation logic for agent calls."""
    max_retries: int = 3

    def _call(
        self,
        agent: AgentProtocol[InputSchema, OutputSchema],
        input: InputSchema,
    ) -> OutputSchema:
        """Call agent, validate JSON, retry boundedly, return typed object."""
        last_err: Exception | None = None
        last_raw: str | None = None

        for attempt in range(1, self.max_retries + 1):
            raw = agent(input.model_dump_json())
            last_raw = raw
            logger.debug(
                f"[dispatcher] {agent.name} attempt {attempt}/{self.max_retries} "
                f"payload={raw[:200]}"
            )
            try:
                return agent.output_schema.model_validate_json(raw)
            except ValidationError as e:
                last_err = e
            except Exception as e:
                last_err = e

        raise RuntimeError(
            f"Agent '{agent.name}' failed after {self.max_retries} retries. "
            f"Last error: {last_err}. Last raw payload: {last_raw}"
        )


@dataclass(kw_only=True)
class AgentDispatcher(Generic[T, R, D], AgentDispatcherBase):
    """
    Generic dispatcher, parametrized by Task (T), Result (R), Decision (D).

    Concrete domains bind these at the domain layer.
    """
    planner: AgentProtocol[PlannerInput[T, R], PlannerOutput[T]]
    worker: AgentProtocol[WorkerInput[T, R], WorkerOutput[R, T]]
    critic: AgentProtocol[CriticInput[T, R], D]

    # inherits max_retries and _call from base

    def plan(self) -> PlannerOutput[T]:
        # Empty PlannerInput for now; you decided planner is stateless
        return self._call(self.planner, PlannerInput[T, R]())

    def work(self, args: WorkerInput[T, R]) -> WorkerOutput[R, T]:
        return self._call(self.worker, args)

    def critique(self, args: CriticInput[T, R]) -> D:
        return self._call(self.critic, args)
