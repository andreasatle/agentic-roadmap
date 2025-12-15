from __future__ import annotations

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
)
from domain.writer.state import StructureState
from domain.writer.schemas import WriterDomainState
from domain.writer.types import WriterResult, WriterTask
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
    if task.operation == "refine":
        new_text = current if text == current else text
    else:
        new_text = text
    sections[task.section_name] = new_text
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
        max_retries=1,
    )

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
    assert draft_response.critic_decision["decision"] == "ACCEPT"
    domain_state = apply_writer_accept(domain_state, draft_task, draft_response)
    assert domain_state.content.sections[section_name].strip() != ""

    refine_response = run_supervisor_once(refine_task, refine_text, domain_state)
    assert refine_response.critic_decision["decision"] == "ACCEPT"
    domain_state = apply_writer_accept(domain_state, refine_task, refine_response)
    combined_text = domain_state.content.sections[section_name]

    refine_again_response = run_supervisor_once(refine_task, combined_text, domain_state)
    assert refine_again_response.critic_decision["decision"] == "ACCEPT"
    domain_state = apply_writer_accept(domain_state, refine_task, refine_again_response)
    final_text = domain_state.content.sections[section_name]

    assert final_text.count(draft_text) == 1
    assert final_text.count(refine_append) == 1
    assert domain_state.structure.sections == ["Intro"]
    assert domain_state.content.section_order is None
    assert domain_state.completed_sections == [section_name]
