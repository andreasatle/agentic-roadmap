"""
Iteration 4 schemas (Pydantic v2).

We add adaptive behavior:
- Worker can inspect previous_result + feedback.
- Critic always returns decision + optional feedback.
- Supervisor controls retries and reconstruction of inputs.

These schemas are the strict contract between agents.
"""

from typing import Literal
from pydantic import BaseModel, Field


# ---------------------------------------------------------
# Core atomic message types
# ---------------------------------------------------------

class Plan(BaseModel):
    """Arithmetic task."""
    op: Literal["ADD", "SUB", "MUL"]
    a: int = Field(..., ge=1, le=20)
    b: int = Field(..., ge=1, le=20)


class Result(BaseModel):
    """Worker's numeric answer."""
    result: int


class Decision(BaseModel):
    """Critic's evaluation."""
    decision: Literal["ACCEPT", "REJECT"]
    # Optional so the Critic can return `null` if desired.
    feedback: str | None = None


# ---------------------------------------------------------
# Agent-specific input/output schemas
# ---------------------------------------------------------

class PlannerInput(BaseModel):
    """Planner receives no information from Supervisor."""
    pass


class PlannerOutput(Plan):
    """Planner outputs a Plan."""
    pass


class WorkerInput(Plan):
    """
    Worker receives:
    - current Plan (op, a, b)
    - previous_result: WorkerOutput.result from last iteration
    - feedback: Critic's explanation (optional)

    These fields guide correction on retries.
    """
    previous_result: int | None = None
    feedback: str | None = None


class WorkerOutput(Result):
    """Worker outputs a single numeric result."""
    pass


class CriticInput(Plan, Result):
    """
    Critic receives:
    - the Plan (op, a, b)
    - the Worker's result
    """
    pass


class CriticOutput(Decision):
    """Critic outputs decision + optional feedback."""
    pass
