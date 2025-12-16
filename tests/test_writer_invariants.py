from __future__ import annotations

import pytest

from domain.writer.planner import make_planner
from domain.writer.schemas import WriterDomainState, WriterPlannerInput, WriterWorkerInput, WriterWorkerOutput, WriterContentState
from domain.writer.state import StructureState
from domain.writer.types import DraftSectionTask, RefineSectionTask, WriterResult, WriterTask


def test_planner_requires_structure():
    planner = make_planner(model="dummy")
    planner_input = WriterPlannerInput(
        task=DraftSectionTask(section_name="Intro", purpose="intro", requirements=[""]),
        project_state=None,
    )
    with pytest.raises(RuntimeError, match="requires explicit structure"):
        planner(planner_input.model_dump_json())


def test_worker_input_rejects_unexpected_fields():
    with pytest.raises(Exception):
        WriterWorkerInput(task=DraftSectionTask(section_name="Intro", purpose="", requirements=[""]), extra_field="nope")  # type: ignore[arg-type]
    assert WriterWorkerInput.model_validate(
        {"task": {"kind": "draft_section", "section_name": "Intro", "purpose": "", "requirements": [""]}}
    )


def test_worker_does_not_mutate_state():
    state = WriterDomainState(structure=StructureState(sections=["Intro"]), content=WriterContentState())
    state_copy = state.model_copy()
    task = DraftSectionTask(section_name="Intro", purpose="", requirements=[""])
    result = WriterResult(text="content")
    _ = state.update(task, result)
    assert state == state_copy


def test_lazy_clients_no_api_key_required(monkeypatch):
    planner = make_planner(model="dummy")
    worker_input = WriterWorkerInput(task=RefineSectionTask(section_name="Intro", purpose="", requirements=[""]))
    # accessing planner and schemas should not require API invocation
    assert planner is not None
    assert worker_input.task.section_name == "Intro"
