from __future__ import annotations

import json

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
    WriterDomainState,
)
from domain.writer.types import WriterResult, WriterTask
from domain.writer.planner import make_planner
from domain.writer.state import StructureState


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


def test_writer_single_task_execution():
    task = WriterTask(
        section_name="Intro",
        purpose="Write intro",
        operation="draft",
        requirements=["Keep it concise"],
    )
    planner_output = WriterPlannerOutput(task=task, worker_id="writer-worker")
    worker_output = WriterWorkerOutput(result=WriterResult(text="done"))
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

    domain_state = WriterDomainState(structure=StructureState(sections=[task.section_name]))
    supervisor = Supervisor(
        dispatcher=dispatcher,
        tool_registry=ToolRegistry(),
        project_state=ProjectState(domain_state=domain_state),
        max_loops=5,
        planner_defaults=WriterPlannerInput(task=task).model_dump(),
        problem_state_cls=problem_state_cls,
    )

    response = supervisor.handle(
        SupervisorRequest(
            control=SupervisorControlInput(max_loops=5),
            domain=SupervisorDomainInput(
                domain_state=domain_state,
                planner_defaults=WriterPlannerInput(task=task).model_dump(),
            ),
        )
    )
    assert response.plan is not None
    assert response.result is not None
    assert response.decision["decision"] == "ACCEPT"
    updated_state = problem_state_cls()().model_validate(response.project_state["domain_state"])
    assert task.section_name in updated_state.content.sections
    assert updated_state.content.sections[task.section_name].strip() != ""
    assert updated_state.completed_sections == [task.section_name]
    assert planner_agent.calls == 1
    assert worker_agent.calls == 1


def test_writer_planner_requires_structure():
    planner = make_planner(client=object(), model="test-model")
    with pytest.raises(Exception):
        planner(json.dumps({"project_state": {}}))
