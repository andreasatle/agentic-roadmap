from agentic.agent_dispatcher import AgentDispatcher

from .types import WriterResult, WriterTask
from .schemas import WriterCriticOutput


class WriterDispatcher(AgentDispatcher[WriterTask, WriterResult, WriterCriticOutput]):
    """Dispatcher binding writer domain generics; no custom routing."""

    pass
