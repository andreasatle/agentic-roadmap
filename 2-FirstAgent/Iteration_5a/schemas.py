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

class ToolRequest(BaseModel):
    """A side-effect request to invoke a registered tool."""
    tool_name: str = Field(..., max_length=64)
    task: Task

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

# Worker emits one of two honest semantic types:
class WorkerOutput(BaseModel):
    result: Result | None = None
    tool_request: ToolRequest | None = None

    @model_validator(mode="after")
    def exactly_one_branch(self) -> WorkerOutput:
        """
        Enforce that exactly one of (result, tool_request) is present.
        Prevents ambiguous payloads and mirrors the prompt contract.
        """
        has_result = self.result is not None
        has_tool = self.tool_request is not None
        if has_result == has_tool:  # both True or both False
            raise ValueError("Provide exactly one of result or tool_request")
        return self

# Critic receives two distinct semantic namespaces explicitly:

class CriticInput(BaseModel):
    plan: Task
    worker_answer: Result  # Supervisor guarantees this is the result branch

CriticOutput = Decision
