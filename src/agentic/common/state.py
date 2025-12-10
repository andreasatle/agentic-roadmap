from pydantic import BaseModel
from agentic.schemas import WorkerOutput


class StatelessProblemState(BaseModel):
    """
    Default domain-level state.
    Provides a no-op update() so state is optional for simple domains.
    """
    def update(self, worker_output: WorkerOutput) -> "StatelessProblemState":
        return self
