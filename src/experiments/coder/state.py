
from typing import Self
from agentic_workflow.common.load_save_mixin import LoadSaveMixin
from experiments.coder.types import CodeResult, CodeTask


class ProblemState(LoadSaveMixin):
    """
    Domain-specific persistent state.
    MUST NOT mutate in-place; always return a new instance from update().
    """

    content: str = ""

    def update(self, task: CodeTask, result: CodeResult) -> Self:
        """
        Return a NEW ProblemState instance updated with accepted worker result.
        Default behavior: no change.
        """
        return self

    def snapshot_for_llm(self) -> dict:
        """
        Return a small, JSON-serializable dictionary containing ONLY the state
        that the LLM should see. Default: expose nothing.
        """
        return {}
