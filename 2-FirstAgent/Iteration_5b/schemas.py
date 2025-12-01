from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field, model_validator

# ---------------------------------------------------------
# Core atomic semantic types
# ---------------------------------------------------------

class Task(BaseModel):
    """A well-bounded arithmetic task."""
    op: Literal["ADD", "SUB", "MUL"]
    a: int = Field(..., ge=1, le=20)
    b: int = Field(..., ge=1, le=20)

class Result(BaseModel):
    """A numeric answer produced by Worker."""
    value: int = Field(..., ge=-10_000, le=10_000)

class Decision(BaseModel):
    """A numeric judgment from Critic."""
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

# Planner has no meaningful input and emits a Task directly:
class PlannerInput(BaseModel):
    pass

PlannerOutput = Task

# Worker consumes a Task plus optional retry guidance fields:
class WorkerInput(BaseModel):
    task: Task
    previous_result: Result | None = None
    feedback: str | None = None
    tool_result: Result | None = None

class WorkerOutput(BaseModel):
    result: Result

# Critic receives two distinct semantic namespaces explicitly:

class CriticInput(BaseModel):
    plan: Task
    worker_answer: Result  # Supervisor guarantees this is the result branch

CriticOutput = Decision
