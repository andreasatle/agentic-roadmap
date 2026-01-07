from agentic_workflow.controller import ControllerDomainInput, ControllerRequest, run_controller
from agentic_workflow.tool_registry import ToolRegistry
from agentic_workflow.agent_dispatcher import AgentDispatcher
from document_writer.domain.writer.types import DraftSectionTask, RefineSectionTask, WriterTask
from document_writer.domain.document.types import DocumentTree
from document_writer.domain.document.validation import validate_definition_authority
from document_writer.domain.document.content import ContentStore
from document_writer.domain.writer.emission import emit_writer_tasks
from document_writer.domain.intent.types import IntentEnvelope
from document_writer.domain.writer.intent_audit import audit_intent_satisfaction, IntentAuditResult
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
    applies_thesis_rule: bool = False,
) -> WriterExecutionResult:
    # Invariant: The writer never introduces conceptual authority. All definition authority is planned upstream.
    validate_definition_authority(document_tree)
    tasks = emit_writer_tasks(
        document_tree,
        content_store,
        intent=intent,
        applies_thesis_rule=applies_thesis_rule,
    )
    for task in tasks:
        if getattr(task, "defines", None) is None or getattr(task, "assumes", None) is None:
            raise ValueError("Writer task must include defines and assumes.")
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
                applies_thesis_rule=current_task.applies_thesis_rule,
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
