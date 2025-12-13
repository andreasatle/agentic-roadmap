from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from agentic.schemas import ProjectState


class SupervisorRunResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    plan: Any | None
    result: Any | None
    decision: Any | None
    loops_used: int
    project_state: ProjectState
    trace: list[Any]
