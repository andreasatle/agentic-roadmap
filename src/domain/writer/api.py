from agentic.supervisor import SupervisorDomainInput, SupervisorRequest, run_supervisor
from agentic.tool_registry import ToolRegistry
from agentic.agent_dispatcher import AgentDispatcher
from domain.writer.schemas import WriterDomainState
from domain.writer.types import WriterTask


def run(
    task: WriterTask,
    *,
    dispatcher: AgentDispatcher,
    tool_registry: ToolRegistry,
    domain_state: WriterDomainState,
):
    """Execute exactly one WriterTask; writer does not manage documents or persistence."""
    supervisor_input = SupervisorRequest(
        domain=SupervisorDomainInput(
            task=task,
            domain_state=domain_state,
        ),
    )
    return run_supervisor(
        supervisor_input,
        dispatcher=dispatcher,
        tool_registry=tool_registry,
    )
