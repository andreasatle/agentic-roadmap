
from typing import Protocol, TypeVar, runtime_checkable
from pydantic import BaseModel


class AgentInput(BaseModel):
    """Marker base-type for agent input schemas."""
    pass


class AgentOutput(BaseModel):
    """Marker base-type for agent output schemas."""
    pass


InputSchema = TypeVar("InputSchema", bound=AgentInput)
OutputSchema = TypeVar("OutputSchema", bound=AgentOutput)


@runtime_checkable
class AgentProtocol(Protocol[InputSchema, OutputSchema]):
    name: str
    input_schema: type[InputSchema]
    output_schema: type[OutputSchema]

    def __call__(self, input_json: str) -> str:  # raw JSON string
        ...


ToolArgs = TypeVar("ToolArgs", bound=BaseModel)
ToolOutput = TypeVar("ToolOutput", bound=BaseModel)

@runtime_checkable
class ToolProtocol(Protocol[ToolArgs, ToolOutput]):
    """Deterministic tool with strongly typed boundary."""
    def __call__(self, args: ToolArgs) -> ToolOutput:
        ...
