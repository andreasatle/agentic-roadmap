from agentic.supervisor import SupervisorDomainInput, SupervisorRequest, run_supervisor
from agentic.tool_registry import ToolRegistry
from agentic.agent_dispatcher import AgentDispatcher
from domain.writer.types import DraftSectionTask, RefineSectionTask, WriterTask


def run(
    task: WriterTask,
    *,
    dispatcher: AgentDispatcher,
    tool_registry: ToolRegistry,
):
    """Execute exactly one writer task; writer does not manage documents or persistence."""
    if not isinstance(task, (DraftSectionTask, RefineSectionTask)):
        raise TypeError("Writer requires a DraftSectionTask or RefineSectionTask.")
    if not task.section_name:
        raise ValueError("Writer task must include section_name.")
    if not task.requirements:
        raise ValueError("Writer task must include explicit requirements.")

    supervisor_input = SupervisorRequest(
        domain=SupervisorDomainInput(
            task=task,
        ),
    )
    return run_supervisor(
        supervisor_input,
        dispatcher=dispatcher,
        tool_registry=tool_registry,
    )
