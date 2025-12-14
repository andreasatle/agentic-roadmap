from __future__ import annotations

import os
from pathlib import Path

from domain.writer.schemas import WriterDomainState
from domain.writer.state import StructureState
from domain.writer.types import WriterResult, WriterTask


def test_writer_state_persistence_round_trip(tmp_path):
    original_cwd = Path.cwd()
    try:
        # isolate persistence
        tmp_cwd = tmp_path / "work"
        tmp_cwd.mkdir()
        os.chdir(tmp_cwd)

        task = WriterTask(section_name="Intro", purpose="", operation="draft", requirements=[""])
        result = WriterResult(text="Intro text")
        state = WriterDomainState(
            structure=StructureState(sections=["Intro", "Body"]),
        )
        state = state.update(task, result)

        state.save(topic="test")
        loaded = WriterDomainState.load(topic="test")

        assert loaded.structure.sections == ["Intro", "Body"]
        assert loaded.content.sections["Intro"] == "Intro text"
        assert loaded.completed_sections == ["Intro"]
    finally:
        os.chdir(original_cwd)
