from agentic.controller import ControllerDomainInput, ControllerRequest, run_controller
from agentic.tool_registry import ToolRegistry
from agentic.agent_dispatcher import AgentDispatcher
from domain.writer.types import DraftSectionTask, RefineSectionTask, WriterTask
from domain.document.types import DocumentTree
from domain.document.content import ContentStore
from domain.writer.emission import emit_writer_tasks
from domain.intent.types import IntentEnvelope
from domain.writer.intent_audit import audit_intent_satisfaction, IntentAuditResult
from dataclasses import dataclass


@dataclass
class WriterExecutionResult:
    """Wrapper returning content plus advisory intent audit; execution is unchanged."""

    content_store: ContentStore
    intent_audit: IntentAuditResult

    def __getattr__(self, item):
        return getattr(self.content_store, item)


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


def execute_document(
    *,
    document_tree: DocumentTree,
    content_store: ContentStore,
    dispatcher: AgentDispatcher,
    tool_registry: ToolRegistry,
    max_refine_attempts: int = 1,
    intent: IntentEnvelope | None = None,
) -> WriterExecutionResult:
    tasks = emit_writer_tasks(document_tree, content_store, intent=intent)
    for task in tasks:
        attempts = 0
        current_task: WriterTask = task
        while attempts <= max_refine_attempts:
            response = run(
                current_task,
                dispatcher=dispatcher,
                tool_registry=tool_registry,
            )
            decision = response.critic_decision
            decision_value = decision.get("decision") if isinstance(decision, dict) else getattr(decision, "decision", None)
            if decision_value == "ACCEPT":
                worker_output = response.worker_output
                result = worker_output.get("result") if isinstance(worker_output, dict) else getattr(worker_output, "result", None)
                text = result.get("text") if isinstance(result, dict) else getattr(result, "text", "")
                if text:
                    content_store.by_node_id[current_task.node_id] = text
                break
            attempts += 1
            if attempts > max_refine_attempts:
                break
            current_task = RefineSectionTask(
                node_id=current_task.node_id,
                section_name=current_task.section_name,
                purpose=current_task.purpose,
                requirements=current_task.requirements,
            )
    intent_audit = audit_intent_satisfaction(
        document_tree=document_tree,
        content_store=content_store,
        intent=intent,
    )
    return WriterExecutionResult(
        content_store=content_store,
        intent_audit=intent_audit,
    )
