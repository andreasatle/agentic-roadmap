from agentic_framework.agent_dispatcher import AgentDispatcher
from agentic_framework.agents.openai import OpenAIAgent
from agentic_framework.controller.transform_controller import TransformController, TransformControllerRequest

from document_writer.domain.editor.api import AgentEditorRequest, AgentEditorResponse


def edit_document(
    request: AgentEditorRequest,
    *,
    dispatcher: AgentDispatcher,
    editor_agent: OpenAIAgent,
) -> AgentEditorResponse:
    controller_request = TransformControllerRequest(
        document=request.document,
        editing_policy=request.editing_policy,
        intent=request.intent,
    )
    controller = TransformController(
        dispatcher=dispatcher,
        agent=editor_agent,
    )
    controller_response = controller(controller_request)
    edited_document = controller_response.edited_document
    if not edited_document or not edited_document.strip():
        raise ValueError("edit_document requires non-empty edited_document.")
    return AgentEditorResponse(
        edited_document=edited_document,
        trace=controller_response.trace,
    )
