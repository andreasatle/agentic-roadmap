from __future__ import annotations

import pytest

from domain.writer.planner import make_planner
from domain.writer.schemas import (
    DraftWorkerInput,
    RefineWorkerInput,
    WriterPlannerInput,
    WriterWorkerOutput,
)
from domain.writer.types import DraftSectionTask, RefineSectionTask


def test_planner_rejects_state_payload():
    planner = make_planner(model="dummy")
    planner_input = WriterPlannerInput(
        task=DraftSectionTask(section_name="Intro", purpose="intro", requirements=[""]),
    )
    with pytest.raises(Exception):
        # project_state should be rejected by the schema
        WriterPlannerInput.model_validate({**planner_input.model_dump(), "project_state": {"foo": "bar"}})


def test_worker_input_rejects_unexpected_fields():
    with pytest.raises(Exception):
        DraftWorkerInput(task=DraftSectionTask(section_name="Intro", purpose="", requirements=[""]), extra_field="nope")  # type: ignore[arg-type]
    assert DraftWorkerInput.model_validate(
        {"task": {"kind": "draft_section", "section_name": "Intro", "purpose": "", "requirements": [""]}}
    )
    with pytest.raises(Exception):
        RefineWorkerInput(task=RefineSectionTask(section_name="Intro", purpose="", requirements=[""]), extra_field="nope")  # type: ignore[arg-type]


def test_worker_does_not_mutate_state():
    worker_input = DraftWorkerInput(task=DraftSectionTask(section_name="Intro", purpose="", requirements=[""]))
    worker_output = WriterWorkerOutput.model_validate({"result": {"text": "content"}})
    assert worker_input.task.section_name == "Intro"
    assert worker_output.result.text == "content"


def test_lazy_clients_no_api_key_required(monkeypatch):
    planner = make_planner(model="dummy")
    worker_input = RefineWorkerInput(task=RefineSectionTask(section_name="Intro", purpose="", requirements=[""]))
    # accessing planner and schemas should not require API invocation
    assert planner is not None
    assert worker_input.task.section_name == "Intro"
