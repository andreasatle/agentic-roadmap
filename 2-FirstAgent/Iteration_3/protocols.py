from typing import Protocol, TypeVar
from pydantic import BaseModel

AgentInput = TypeVar("Input", bound=BaseModel)  # Input schema type
AgentOutput = TypeVar("Ooutput", bound=BaseModel)  # Output schema type

class AgentProtocol(Protocol[AgentInput, AgentOutput]):
    """
    All agents declare:
        - the schema of what they accept (Input)
        - the schema of what they return (Output)

    They still operate via string I/O because they are LLM-facing,
    but the Supervisor handles JSON serialization/validation.
    """

    def __call__(self, user_input: str) -> str:
        ...

    @property
    def name(self) -> str:
        ...

    @property
    def input_schema(self) -> type[AgentInput]:
        ...

    @property
    def output_schema(self) -> type[AgentOutput]:
        ...