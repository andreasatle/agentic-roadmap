from __future__ import annotations

from domain.writer.schemas import WriterDomainState
from domain.writer.state import StructureState
from domain.writer.types import WriterResult, WriterTask


def test_writer_snapshot_exposes_only_names_and_order():
    task = WriterTask(
        section_name="Intro",
        purpose="Write intro",
        operation="draft",
        requirements=["State purpose"],
    )
    result = WriterResult(text="Intro text")
    state = WriterDomainState(
        completed_sections=["Intro"],
        structure=StructureState(sections=["Intro", "Body", "Conclusion"]),
    )
    updated_state = state.update(task, result)

    snapshot = updated_state.snapshot_for_llm()

    assert "completed_sections" in snapshot
    assert "section_order" in snapshot
    assert "content" not in snapshot
    assert "sections" not in snapshot
    assert snapshot["completed_sections"] == ["Intro"]
    assert snapshot["section_order"] == ["Intro", "Body", "Conclusion"]
