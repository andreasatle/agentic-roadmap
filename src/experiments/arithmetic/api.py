from agentic_workflow.controller import ControllerDomainInput, ControllerRequest, run_controller
from agentic_workflow.tool_registry import ToolRegistry
from agentic_workflow.agent_dispatcher import AgentDispatcher
from experiments.arithmetic.types import ArithmeticTask


def run(
    task: ArithmeticTask,
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
