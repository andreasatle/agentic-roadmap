from __future__ import annotations

from typing import Literal, TypeVar, Generic
from pydantic import BaseModel, Field, model_validator

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
    



T = TypeVar("T")  # Task
R = TypeVar("R")  # Result
D = TypeVar("D")  # Decision
TR = TypeVar("TR")  # Tool Request Args

class ToolRequest(BaseModel, Generic[TR]):
    """A side-effect request to invoke a registered tool."""
    tool_name: str = Field(..., max_length=64)
    args: TR

class PlannerInput(BaseModel, Generic[T, R]):
    pass

class PlannerOutput(BaseModel, Generic[T]):
    task: T

class WorkerInput(BaseModel, Generic[T, R]):
    task: T
    previous_result: R | None = None
    feedback: str | None = None
    tool_result: R | None = None

class WorkerOutput(ConstrainedXOROutput, Generic[R, TR]):
    result: R | None = None
    tool_request: ToolRequest[TR] | None = None

class CriticInput(BaseModel, Generic[T, R]):
    """Critic sees the original plan and the Worker’s answer."""
    plan: T
    worker_answer: R

class CriticOutput(BaseModel, Generic[D]):
    """Critic output wrapper for decision payloads."""
    decision: D
