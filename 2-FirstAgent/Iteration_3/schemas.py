"""
Iteration 3 schemas (Pydantic v2).

We now *type* every agent message. The Supervisor validates these types
before passing data downstream. Any malformed JSON or schema mismatch
triggers a bounded retry, not a crash.

Key point:
- These schemas are the *contract* between agents.
- Agents may hallucinate content, but they cannot break the contract
  without being caught and retried.
"""

from typing import Literal
from pydantic import BaseModel, Field


class Plan(BaseModel):
    op: Literal["ADD", "SUB", "MUL"]
    a: int = Field(..., ge=1, le=20)
    b: int = Field(..., ge=1, le=20)


class Result(BaseModel):
    result: int

class Decision(BaseModel):
    decision: Literal["ACCEPT", "REJECT"]


class PlannerInput(BaseModel):
    pass

class PlannerOutput(Plan):
    pass

class WorkerInput(Plan):
    pass

class WorkerOutput(Result):
    pass

class CriticInput(Plan, Result):
    pass

class CriticOutput(Decision):
    pass
