from __future__ import annotations
from typing import Protocol, runtime_checkable
from pydantic import BaseModel


@runtime_checkable
class DomainStateProtocol(Protocol):
    def update(self, task, result):
        ...

    def snapshot_for_llm(self) -> dict:
        ...


class StatelessProblemState(BaseModel):
    """
    Default domain-level state.
    Optional per-domain accumulation. Does nothing by default.
    """

    def update(self, task, result):
        """
        No-op state update for stateless domains.
        Must exist so that the supervisor can uniformly call update().
        """
        return self

    def snapshot_for_llm(self) -> dict:
        """
        Return a small, JSON-serializable dictionary containing ONLY the state
        that the LLM should see. Stateless domains expose nothing.
        """
        return {}
