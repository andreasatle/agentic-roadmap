from __future__ import annotations

import pytest

from agentic.agent_dispatcher import AgentDispatcher
from agentic.schemas import ProjectState
from agentic.supervisor import Supervisor, SupervisorControlInput, SupervisorDomainInput, SupervisorRequest
from agentic.tool_registry import ToolRegistry
from domain.writer.factory import problem_state_cls
from domain.writer.schemas import (
    WriterPlannerInput,
    WriterPlannerOutput,
    WriterWorkerInput,
    WriterWorkerOutput,
    WriterCriticInput,
    WriterCriticOutput,
)
from domain.writer.state import StructureState
from domain.writer.schemas import WriterDomainState
from domain.writer.types import WriterResult, WriterTask


class DummyAgent:
    def __init__(self, input_schema, output_schema, output_json: str, name: str):
        self.name = name
        self.id = name
        self.input_schema = input_schema
        self.output_schema = output_schema
        self.output_json = output_json
        self.calls = 0

    def __call__(self, _input_json: str) -> str:
        self.calls += 1
        return self.output_json


def run_supervisor_once(task: WriterTask, worker_text: str, domain_state: WriterDomainState):
    planner_output = WriterPlannerOutput(task=task, worker_id="writer-worker")
    worker_output = WriterWorkerOutput(result=WriterResult(text=worker_text))
    critic_output = WriterCriticOutput(decision="ACCEPT")

    planner_agent = DummyAgent(WriterPlannerInput, WriterPlannerOutput, planner_output.model_dump_json(), "planner")
    worker_agent = DummyAgent(WriterWorkerInput, WriterWorkerOutput, worker_output.model_dump_json(), "worker")
    critic_agent = DummyAgent(WriterCriticInput, WriterCriticOutput, critic_output.model_dump_json(), "critic")

    dispatcher = AgentDispatcher(
        planner=planner_agent,
        workers={"writer-worker": worker_agent},
        critic=critic_agent,
        domain_name="writer",
        max_retries=1,
    )

    supervisor = Supervisor(
        dispatcher=dispatcher,
        tool_registry=ToolRegistry(),
        project_state=ProjectState(domain_state=domain_state),
        max_loops=5,
        problem_state_cls=problem_state_cls,
    )

    response = supervisor.handle(
        SupervisorRequest(
            control=SupervisorControlInput(max_loops=5),
            domain=SupervisorDomainInput(
                domain_state=domain_state,
                task=task,
            ),
        )
    )
    return response


def test_refine_is_idempotent_and_appends_once():
    section_name = "Intro"
    draft_text = "Draft content."
    refine_append = "Refined addition."
    refine_text = f"{draft_text}\n\n{refine_append}"

    draft_task = WriterTask(
        section_name=section_name,
        purpose="Write intro",
        operation="draft",
        requirements=["Provide an introduction."],
    )
    refine_task = WriterTask(
        section_name=section_name,
        purpose="Refine intro",
        operation="refine",
        requirements=["Improve clarity."],
    )

    domain_state = WriterDomainState(structure=StructureState(sections=[section_name]))

    draft_response = run_supervisor_once(draft_task, draft_text, domain_state)
    assert draft_response.decision["decision"] == "ACCEPT"
    domain_state = WriterDomainState(**draft_response.project_state["domain_state"])
    assert domain_state.content.sections[section_name].strip() != ""

    refine_response = run_supervisor_once(refine_task, refine_text, domain_state)
    assert refine_response.decision["decision"] == "ACCEPT"
    domain_state = WriterDomainState(**refine_response.project_state["domain_state"])
    combined_text = domain_state.content.sections[section_name]

    refine_again_response = run_supervisor_once(refine_task, combined_text, domain_state)
    assert refine_again_response.decision["decision"] == "ACCEPT"
    domain_state = WriterDomainState(**refine_again_response.project_state["domain_state"])
    final_text = domain_state.content.sections[section_name]

    assert final_text.count(draft_text) == 1
    assert final_text.count(refine_append) == 1
    assert domain_state.structure.sections == ["Intro"]
    assert domain_state.content.section_order is None
    assert domain_state.completed_sections == [section_name]
