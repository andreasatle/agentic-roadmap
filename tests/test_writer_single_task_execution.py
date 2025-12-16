
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
)
from domain.writer.types import DraftSectionTask, WriterResult
from domain.writer.planner import make_planner


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
    task = DraftSectionTask(
        section_name="Intro",
        purpose="Write intro",
        requirements=["Keep it concise"],
    )
    planner_output = WriterPlannerOutput(task=task, worker_id="writer-draft-worker")
    worker_output = WriterWorkerOutput(result=WriterResult(text="done"))
    critic_output = WriterCriticOutput(decision="ACCEPT")

    planner_agent = DummyAgent(WriterPlannerInput, WriterPlannerOutput, planner_output.model_dump_json(), "planner")
    worker_agent = DummyAgent(WriterWorkerInput, WriterWorkerOutput, worker_output.model_dump_json(), "worker-draft-worker")
    critic_agent = DummyAgent(WriterCriticInput, WriterCriticOutput, critic_output.model_dump_json(), "critic")

    dispatcher = AgentDispatcher(
        planner=planner_agent,
        workers={"writer-draft-worker": worker_agent},
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
                task=task,
            ),
        )
    )
    assert response.task["section_name"] == task.section_name
    assert response.worker_output["result"]["text"] == "done"
    assert response.critic_decision["decision"] == "ACCEPT"
    assert planner_agent.calls == 1
    assert worker_agent.calls == 1


def test_writer_planner_requires_task():
    planner = make_planner(model="test-model")
    with pytest.raises(RuntimeError, match="requires an explicit task"):
        planner(json.dumps({}))
