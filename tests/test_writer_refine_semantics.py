
from agentic.agent_dispatcher import AgentDispatcher
from agentic.controller import Controller, ControllerDomainInput, ControllerRequest
from agentic.tool_registry import ToolRegistry
from domain.document_writer.writer.schemas import (
    WriterPlannerInput,
    WriterPlannerOutput,
    DraftWorkerInput,
    RefineWorkerInput,
    WriterWorkerOutput,
    WriterCriticInput,
    WriterCriticOutput,
)
from domain.document_writer.writer.types import DraftSectionTask, RefineSectionTask, WriterResult, WriterTask


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


def run_controller_once(task: WriterTask, worker_text: str):
    worker_id = "writer-draft-worker" if isinstance(task, DraftSectionTask) else "writer-refine-worker"
    planner_output = WriterPlannerOutput(task=task, worker_id=worker_id)
    worker_output = WriterWorkerOutput(result=WriterResult(text=worker_text))
    critic_output = WriterCriticOutput(decision="ACCEPT")

    planner_agent = DummyAgent(WriterPlannerInput, WriterPlannerOutput, planner_output.model_dump_json(), "planner")
    worker_input_schema = DraftWorkerInput if worker_id == "writer-draft-worker" else RefineWorkerInput
    worker_agent = DummyAgent(worker_input_schema, WriterWorkerOutput, worker_output.model_dump_json(), worker_id)
    critic_agent = DummyAgent(WriterCriticInput, WriterCriticOutput, critic_output.model_dump_json(), "critic")

    dispatcher = AgentDispatcher(
        planner=planner_agent,
        workers={worker_id: worker_agent},
        critic=critic_agent,
        max_retries=1,
    )

    controller = Controller(
        dispatcher=dispatcher,
        tool_registry=ToolRegistry(),
    )

    response = controller(
        ControllerRequest(
            domain=ControllerDomainInput(
                task=task,
            ),
        )
    )
    return response


def test_refine_is_idempotent_and_appends_once():
    section_name = "Intro"
    draft_task = DraftSectionTask(
        node_id=section_name,
        section_name=section_name,
        purpose="Write intro",
        requirements=["Provide an introduction."],
    )
    refine_task = RefineSectionTask(
        node_id=section_name,
        section_name=section_name,
        purpose="Refine intro",
        requirements=["Improve clarity."],
    )

    draft_response = run_controller_once(draft_task, "Draft content.")
    assert draft_response.worker_id == "writer-draft-worker"
    assert draft_response.critic_decision["decision"] == "ACCEPT"

    refine_response = run_controller_once(refine_task, "Refined content.")
    assert refine_response.worker_id == "writer-refine-worker"
    assert refine_response.critic_decision["decision"] == "ACCEPT"
