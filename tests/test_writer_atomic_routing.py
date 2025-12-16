from __future__ import annotations

import pytest

from domain.writer.planner import make_planner
from domain.writer.schemas import WriterDomainState, WriterPlannerInput, WriterPlannerOutput, WriterWorkerInput
from domain.writer.state import StructureState
from domain.writer.types import DraftSectionTask, RefineSectionTask


def test_planner_routes_draft_and_refine_to_distinct_workers():
    planner = make_planner(model="dummy")
    domain_state = WriterDomainState(structure=StructureState(sections=["Intro"]))

    draft_input = WriterPlannerInput(
        task=DraftSectionTask(section_name="Intro", purpose="draft intro", requirements=["req"]),
        project_state=domain_state,
    )
    draft_output = WriterPlannerOutput.model_validate_json(planner(draft_input.model_dump_json()))
    assert draft_output.worker_id == "writer-draft-worker"
    assert draft_output.task == draft_input.task

    refine_input = WriterPlannerInput(
        task=RefineSectionTask(section_name="Intro", purpose="refine intro", requirements=["req"]),
        project_state=domain_state,
    )
    refine_output = WriterPlannerOutput.model_validate_json(planner(refine_input.model_dump_json()))
    assert refine_output.worker_id == "writer-refine-worker"
    assert refine_output.task == refine_input.task


def test_planner_rejects_missing_section_and_worker_input_requires_kind():
    planner = make_planner(model="dummy")
    domain_state = WriterDomainState(structure=StructureState(sections=["Intro"]))
    bad_input = WriterPlannerInput(
        task=DraftSectionTask(section_name="Missing", purpose="missing", requirements=["req"]),
        project_state=domain_state,
    )
    with pytest.raises(RuntimeError, match="cannot invent section"):
        planner(bad_input.model_dump_json())

    with pytest.raises(Exception):
        WriterWorkerInput.model_validate({"task": {"section_name": "Intro", "purpose": "p", "requirements": ["r"]}})
