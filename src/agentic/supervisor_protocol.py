from __future__ import annotations

from typing import Protocol

from agentic.supervisor import SupervisorRequest, SupervisorResponse


class SupervisorProtocol(Protocol):
    def handle(self, request: SupervisorRequest) -> SupervisorResponse:
        ...
