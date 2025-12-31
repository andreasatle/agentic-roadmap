
from agentic.agent_dispatcher import AgentDispatcher
from agentic.controller import Controller, ControllerDomainInput, ControllerRequest
from agentic.tool_registry import ToolRegistry
from domain.document_writer.writer.schemas import (
    WriterPlannerInput,
    WriterPlannerOutput,
    DraftWorkerInput,
    WriterWorkerOutput,
    WriterCriticInput,
    WriterCriticOutput,
)
from domain.document_writer.writer.types import DraftSectionTask, WriterResult


class SequenceAgent:
    def __init__(self, input_schema, output_schema, outputs: list[str], name: str):
        self.name = name
        self.id = name
        self.input_schema = input_schema
        self.output_schema = output_schema
        self._outputs = outputs
        self.calls = 0

    def __call__(self, _input_json: str) -> str:
        self.calls += 1
        if not self._outputs:
            raise RuntimeError("No more scripted outputs")
        return self._outputs.pop(0)


def test_writer_reject_then_accept():
    section_name = "Intro"
    initial_task = DraftSectionTask(
        node_id=section_name,
        section_name=section_name,
        purpose="Initial intro",
        requirements=["State intro"],
    )

    planner_outputs = [
        WriterPlannerOutput(task=initial_task, worker_id="writer-draft-worker").model_dump_json(),
        WriterPlannerOutput(task=initial_task, worker_id="writer-draft-worker").model_dump_json(),
    ]
    worker_outputs = [
        WriterWorkerOutput(result=WriterResult(text="bad")).model_dump_json(),
        WriterWorkerOutput(result=WriterResult(text="good")).model_dump_json(),
    ]
    critic_outputs = [
        WriterCriticOutput(decision="REJECT", feedback={"kind": "OTHER", "message": "Fix"}).model_dump_json(),
        WriterCriticOutput(decision="ACCEPT").model_dump_json(),
    ]

    planner_agent = SequenceAgent(WriterPlannerInput, WriterPlannerOutput, planner_outputs, "planner")
    worker_agent = SequenceAgent(DraftWorkerInput, WriterWorkerOutput, worker_outputs, "worker-draft-worker")
    critic_agent = SequenceAgent(WriterCriticInput, WriterCriticOutput, critic_outputs, "critic")

    dispatcher = AgentDispatcher(
        planner=planner_agent,
        workers={"writer-draft-worker": worker_agent},
        critic=critic_agent,
        max_retries=1,
    )

    controller = Controller(
        dispatcher=dispatcher,
        tool_registry=ToolRegistry(),
    )

    reject_response = controller(
        ControllerRequest(
            domain=ControllerDomainInput(
                task=initial_task,
            ),
        )
    )

    accept_response = controller(
        ControllerRequest(
            domain=ControllerDomainInput(
                task=initial_task,
            ),
        )
    )

    assert planner_agent.calls == 2
    assert worker_agent.calls == 2
    assert critic_agent.calls == 2
    assert reject_response.critic_decision["decision"] == "REJECT"
    assert accept_response.critic_decision["decision"] == "ACCEPT"
