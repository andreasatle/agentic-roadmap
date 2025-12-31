from agentic.tool_registry import ToolRegistry
from domain.document_writer.writer.dispatcher import WriterDispatcher
from domain.document_writer.writer.planner import make_planner
from domain.document_writer.writer.draft_worker import make_draft_worker
from domain.document_writer.writer.refine_worker import make_refine_worker
from domain.document_writer.writer.critic import make_critic


def make_agent_dispatcher(
    model: str = "gpt-4.1-mini",
    max_retries: int = 3,
) -> WriterDispatcher:
    planner = make_planner(model=model)
    draft_worker = make_draft_worker(model=model)
    refine_worker = make_refine_worker(model=model)
    critic = make_critic(model=model)
    return WriterDispatcher(
        max_retries=max_retries,
        planner=planner,
        workers={
            "writer-draft-worker": draft_worker,
            "writer-refine-worker": refine_worker,
        },
        critic=critic,
    )


def make_tool_registry() -> ToolRegistry:
    # Writer domain uses no tools in the MVP.
    return ToolRegistry()
