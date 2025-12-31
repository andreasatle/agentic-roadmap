from __future__ import annotations

import json

import pytest

from domain.document_writer.writer.planner import make_planner
from domain.document_writer.writer.schemas import DraftWorkerInput, WriterPlannerInput, WriterPlannerOutput
from domain.document_writer.writer.types import DraftSectionTask, RefineSectionTask


def test_planner_routes_draft_and_refine_to_distinct_workers():
    planner = make_planner(model="dummy")

    draft_input = WriterPlannerInput(
        task=DraftSectionTask(node_id="Intro", section_name="Intro", purpose="draft intro", requirements=["req"]),
    )
    draft_output = WriterPlannerOutput.model_validate_json(planner(draft_input.model_dump_json()))
    assert draft_output.worker_id == "writer-draft-worker"
    assert draft_output.task == draft_input.task

    refine_input = WriterPlannerInput(
        task=RefineSectionTask(node_id="Intro", section_name="Intro", purpose="refine intro", requirements=["req"]),
    )
    refine_output = WriterPlannerOutput.model_validate_json(planner(refine_input.model_dump_json()))
    assert refine_output.worker_id == "writer-refine-worker"
    assert refine_output.task == refine_input.task


def test_writer_planner_requires_discriminated_task():
    planner = make_planner(model="dummy")
    invalid_payloads = [
        "{}",
        json.dumps({"task": {}}),
        json.dumps({"task": {"section_name": "Intro"}}),
        json.dumps({"task": {"kind": "unknown", "section_name": "Intro", "purpose": "p", "requirements": ["r"]}}),
    ]
    for payload in invalid_payloads:
        with pytest.raises(RuntimeError):
            planner(payload)
