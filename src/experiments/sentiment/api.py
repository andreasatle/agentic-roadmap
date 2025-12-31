from agentic.controller import ControllerDomainInput, ControllerRequest, run_controller
from agentic.tool_registry import ToolRegistry
from agentic.agent_dispatcher import AgentDispatcher
from domain.sentiment.types import SentimentTask


def run(
    task: SentimentTask,
    *,
    dispatcher: AgentDispatcher,
    tool_registry: ToolRegistry,
):
    controller_input = ControllerRequest(
        domain=ControllerDomainInput(
            task=task,
        ),
    )
    return run_controller(
        controller_input,
        dispatcher=dispatcher,
        tool_registry=tool_registry,
    )
