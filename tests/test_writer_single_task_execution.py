from __future__ import annotations

import json

import pytest

from agentic.agent_dispatcher import AgentDispatcher
from agentic.supervisor import Supervisor, SupervisorDomainInput, SupervisorRequest
from agentic.tool_registry import ToolRegistry
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
from agentic.supervisor import SupervisorResponse


def apply_writer_accept(state: WriterDomainState, task: WriterTask, response: SupervisorResponse) -> WriterDomainState:
    decision = response.critic_decision
    decision_value = decision.get("decision") if isinstance(decision, dict) else getattr(decision, "decision", None)
    if decision_value != "ACCEPT":
        return state
    worker_output = response.worker_output
    if worker_output is None:
        return state
    if isinstance(worker_output, dict):
        result = worker_output.get("result") if isinstance(worker_output.get("result"), dict) else worker_output.get("result")
        text = result.get("text") if isinstance(result, dict) else ""
    else:
        result = getattr(worker_output, "result", None)
        text = getattr(result, "text", "") if result else ""
    if not text:
        return state
    sections = dict(state.content.sections or {})
    current = sections.get(task.section_name, "")
    if task.operation == "refine" and text != current:
        sections[task.section_name] = text
    else:
        sections[task.section_name] = text if task.operation == "draft" else current or text
    completed = list(state.completed_sections or [])
    if task.section_name not in completed:
        completed.append(task.section_name)
    new_content = state.content.model_copy(update={"sections": sections})
    return state.model_copy(update={"content": new_content, "completed_sections": completed})


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
        max_retries=1,
    )

    domain_state = WriterDomainState(structure=StructureState(sections=[task.section_name]))
    supervisor = Supervisor(
        dispatcher=dispatcher,
        tool_registry=ToolRegistry(),
    )

    response = supervisor(
        SupervisorRequest(
            domain=SupervisorDomainInput(
                domain_state=domain_state,
                task=task,
            ),
        )
    )
    assert response.task is not None
    assert response.worker_output is not None
    assert response.critic_decision["decision"] == "ACCEPT"
    updated_state = apply_writer_accept(domain_state, task, response)
    assert task.section_name in updated_state.content.sections
    assert updated_state.content.sections[task.section_name].strip() != ""
    assert updated_state.completed_sections == [task.section_name]
    assert planner_agent.calls == 1
    assert worker_agent.calls == 1


def test_writer_planner_requires_structure():
    planner = make_planner(client=object(), model="test-model")
    with pytest.raises(Exception):
        planner(json.dumps({}))
