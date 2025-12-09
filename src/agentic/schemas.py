from __future__ import annotations

from typing import Literal, TypeVar, Generic, Final, Any
from pydantic import BaseModel, Field, model_validator
from dataclasses import dataclass, field
from uuid import uuid4

# ---------------------------------------------------------
# Core atomic semantic types
# ---------------------------------------------------------


class Decision(BaseModel):
    """A judgment from Critic."""
    decision: Literal["ACCEPT", "REJECT"]
    feedback: str | None = None

    @model_validator(mode="after")
    def require_feedback_on_reject(self) -> Decision:
        """
        Enforce that REJECT decisions include a non-empty feedback string.
        Keeps ACCEPT decisions lightweight while preserving traceability on failures.
        """
        if self.decision == "REJECT":
            if not (self.feedback and self.feedback.strip()):
                raise ValueError("feedback is required when decision == 'REJECT'")
        return self

# ---------------------------------------------------------
# Agent input/output contracts
# ---------------------------------------------------------


class ConstrainedXOROutput(BaseModel):
    """Superclass that enforces exactly one active branch over child fields."""

    @model_validator(mode="after")
    def enforce_xor(self):
        # Count all non-null fields on the instance
        non_null_count = sum(
            1 for _, v in self.__dict__.items() if v is not None
        )
        if non_null_count != 1:
            raise ValueError(
                f"Exactly one branch must be active, found {non_null_count}"
            )
        return self
    


class HistoryEntry(BaseModel):
    state: str
    worker_id: str | None = None
    plan: dict | None = None
    result: dict | None = None
    decision: dict | None = None


class ProjectState(BaseModel):
    """
    A persistent per-run state object that accumulates metadata across supervisor cycles.
    This is domain-agnostic, and fields are intentionally minimal.
    """
    cycle: int = 0
    history: list[HistoryEntry] = Field(default_factory=list)
    last_plan: dict | None = None
    last_result: dict | None = None
    last_decision: dict | None = None


T = TypeVar("T")  # Task
R = TypeVar("R")  # Result
D = TypeVar("D")  # Decision
TR = TypeVar("TR")  # Tool Request Args

class ToolRequest(BaseModel):
    """A side-effect request to invoke a registered tool."""
    tool_name: str = Field(..., max_length=64)
    args: Any

class PlannerInput(BaseModel, Generic[T, R]):
    """
    Optional context passed to the Planner so it can correct previous mistakes.
    """
    feedback: str | None = None
    previous_task: T | None = None
    previous_worker_id: str | None = None
    random_seed: str | None = None
    project_state: ProjectState | None = None

class PlannerOutput(BaseModel, Generic[T]):
    task: T
    worker_id: str

class WorkerInput(BaseModel, Generic[T, R]):
    task: T
    previous_result: R | None = None
    feedback: str | None = None
    tool_result: R | None = None

class WorkerOutput(ConstrainedXOROutput, Generic[R]):
    result: R | None = None
    tool_request: ToolRequest | None = None

class CriticInput(BaseModel, Generic[T, R]):
    """Critic sees the original plan and the Worker’s answer."""
    plan: T
    worker_answer: R
    project_state: ProjectState | None = None

class CriticOutput(BaseModel, Generic[D]):
    """Critic output wrapper for decision payloads."""
    decision: D


AgentOutput = TypeVar("AgentOutput")  # Output type (PlannerOutput, WorkerOutput, Decision, etc.)

@dataclass(frozen=True)
class AgentCallResult(Generic[AgentOutput]):
    """
    Wraps the output of an agent call together with the agent's identity.
    Frozen to prevent accidental mutation.
    """
    output: AgentOutput
    agent_id: str
    call_id: Final[str] = field(default_factory=lambda: str(uuid4()))
