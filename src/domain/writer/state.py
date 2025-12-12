from __future__ import annotations

from pydantic import BaseModel, Field

from agentic.common.load_save_mixin import LoadSaveMixin
from domain.writer.types import WriterResult, WriterTask


class WriterContentState(LoadSaveMixin):
    sections: dict[str, str] = Field(default_factory=dict)
    section_order: list[str] | None = None

    def update(
        self,
        task: WriterTask,
        result: WriterResult,
        *,
        section_order: list[str] | None = None,
    ) -> "WriterContentState":
        # Copy sections immutably
        new_sections = dict(self.sections)
        section_name = getattr(task, "section_name", None)
        operation = getattr(task, "operation", None)
        if section_name:
            existing_text = new_sections.get(section_name)
            if existing_text is None or operation == "refine":
                new_sections[section_name] = result.text

        # Determine updated section_order
        new_order = self.section_order
        if section_order is not None and not self.section_order:
            new_order = section_order

        # Build new instance with all existing fields preserved
        base = self.model_dump()
        base["sections"] = new_sections
        base["section_order"] = new_order

        return self.__class__(**base)

    def snapshot_for_llm(self) -> dict:
        """
        Return a small, JSON-serializable dictionary containing ONLY the state
        that the LLM should see. Expose section names only.
        """
        return {}
