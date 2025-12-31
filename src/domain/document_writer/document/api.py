from agentic.agent_dispatcher import AgentDispatcher
from agentic.analysis_controller import (
    AnalysisControllerRequest,
    run_analysis_controller,
)
from domain.document_writer.document.schemas import DocumentPlannerInput
from domain.document_writer.document.types import DocumentTree
from domain.document_writer.intent.types import IntentEnvelope
from dataclasses import dataclass


@dataclass
class DocumentAnalysisResult:
    """Domain-owned wrapper adding intent observability; behavior is unchanged and delegated."""

    controller_response: any
    intent_observation: str

    def __getattr__(self, item):
        return getattr(self.controller_response, item)


def analyze(
    *,
    document_tree: DocumentTree | None,
    tone: str | None,
    audience: str | None,
    goal: str | None,
    intent: IntentEnvelope | None = None,
    dispatcher: AgentDispatcher,
):
    intent_observation: str
    if document_tree is not None:
        intent_observation = "ignored_existing_structure"
    else:
        intent_observation = "intent_advisory_available" if intent is not None else "no_intent_provided"

    planner_input = DocumentPlannerInput(
        document_tree=document_tree,
        tone=tone,
        audience=audience,
        goal=goal,
        intent=intent,
    )
    controller_input = AnalysisControllerRequest(planner_input=planner_input)
    controller_response = run_analysis_controller(
        controller_input,
        dispatcher=dispatcher,
    )
    return DocumentAnalysisResult(
        controller_response=controller_response,
        intent_observation=intent_observation,
    )
