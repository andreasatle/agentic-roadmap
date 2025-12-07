from dataclasses import dataclass
from typing import Generic, TypeVar

from agentic.schemas import (
    PlannerInput,
    PlannerOutput,
    WorkerInput,
    WorkerOutput,
    CriticInput,
    AgentCallResult
)
from agentic.protocols import AgentProtocol, InputSchema, OutputSchema
from pydantic import ValidationError
from agentic.logging_config import get_logger

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
    workers: dict[str, AgentProtocol[WorkerInput[T, R], WorkerOutput[R]]]
    critic: AgentProtocol[CriticInput[T, R], D]

    # inherits max_retries and _call from base

    def plan(self, planner_input: PlannerInput[T, R] | None = None) -> AgentCallResult[PlannerOutput[T]]:
        if planner_input is None:
            planner_input = PlannerInput[T, R]()
        output: PlannerOutput[T] = self._call(self.planner, planner_input)
        return AgentCallResult(agent_id=self.planner.id, output=output)

    def work(self, worker_id: str, args: WorkerInput[T, R]) -> AgentCallResult[WorkerOutput[R]]:
        last_err: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                worker_agent = self.workers.get(worker_id)
                if worker_agent is None:
                    raise ValueError(f"Unknown worker_id '{worker_id}'")
                logger.debug(
                    f"[dispatcher] worker attempt {attempt}/{self.max_retries} "
                    f"routing_id={worker_id}"
                )
                output: WorkerOutput[R] = self._call(worker_agent, args)
                return AgentCallResult(agent_id=worker_agent.id, output=output)
            except Exception as e:
                last_err = e
                continue

        raise RuntimeError(
            f"Worker routing failed after {self.max_retries} retries. "
            f"Last error: {last_err}"
        )

    def critique(self, args: CriticInput[T, R]) -> AgentCallResult[D]:
        output: D = self._call(self.critic, args)
        return AgentCallResult(agent_id=self.critic.id, output=output)
