from __future__ import annotations

import pytest

from domain.writer.planner import make_planner
from domain.writer.schemas import WriterPlannerInput, WriterPlannerOutput, WriterWorkerInput
from domain.writer.types import DraftSectionTask, RefineSectionTask


def test_planner_routes_draft_and_refine_to_distinct_workers():
    planner = make_planner(model="dummy")

    draft_input = WriterPlannerInput(
        task=DraftSectionTask(section_name="Intro", purpose="draft intro", requirements=["req"]),
    )
    draft_output = WriterPlannerOutput.model_validate_json(planner(draft_input.model_dump_json()))
    assert draft_output.worker_id == "writer-draft-worker"
    assert draft_output.task == draft_input.task

    refine_input = WriterPlannerInput(
        task=RefineSectionTask(section_name="Intro", purpose="refine intro", requirements=["req"]),
    )
    refine_output = WriterPlannerOutput.model_validate_json(planner(refine_input.model_dump_json()))
    assert refine_output.worker_id == "writer-refine-worker"
    assert refine_output.task == refine_input.task


def test_planner_rejects_missing_section_and_worker_input_requires_kind():
    planner = make_planner(model="dummy")
    with pytest.raises(RuntimeError, match="requires an explicit task"):
        planner("{}")

    with pytest.raises(Exception):
        WriterWorkerInput.model_validate({"task": {"section_name": "Intro", "purpose": "p", "requirements": ["r"]}})
