from typing import Protocol, TypeVar, Any
from pydantic import BaseModel

AgentInput = TypeVar("AgentInput", bound=BaseModel)  # Input schema type
AgentOutput = TypeVar("AgentOutput", bound=BaseModel)  # Output schema type

class AgentProtocol(Protocol[AgentInput, AgentOutput]):
    """
    All agents declare:
        - the schema of what they accept (Input)
        - the schema of what they return (Output)

    They still operate via string I/O because they are LLM-facing,
    but the Supervisor handles JSON serialization/validation.
    """

    name: str
    input_schema: type[AgentInput]
    output_schema: type[AgentOutput]

    def __call__(self, user_input: str) -> str:
        ...

class ToolProtocol(Protocol):

    name: str

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        ...