from typing import TypeVar, Generic, Protocol, runtime_checkable, Callable
from pydantic import BaseModel
from .protocols import ToolProtocol, ToolArgs, ToolOutput

class ToolRegistry(Generic[ToolArgs, ToolOutput]):
    """Strongly typed registry for deterministic tools."""

    # Storage does NOT branch on generics; it simply stores entries by name
    _tools: dict[str, tuple[str, ToolProtocol, type[ToolArgs]]]

    def __init__(self):
        self._tools = {}

    def register(
        self,
        name: str,
        description: str,
        func: ToolProtocol[ToolArgs, ToolOutput],
        arg_type: type[ToolArgs],
    ) -> None:
        """Register a tool and its argument contract."""
        self._tools[name] = (description, func, arg_type)

    def get(self, name: str) -> tuple[str, ToolProtocol, type[ToolArgs]] | None:
        """Return a tool entry or None."""
        entry = self._tools.get(name)
        return None if entry is None else entry

    def call(self, name: str, args: ToolArgs) -> ToolOutput:
        """Invoke the tool exactly once via protocol and validate its args type."""
        entry = self.get(name)
        if entry is None:
            raise RuntimeError(f"Unknown tool: {name}")

        description, func, arg_type = entry 
        # Validate the argument type early at the boundary
        if not isinstance(args, arg_type):
            raise TypeError(f"Args for '{name}' must be {arg_type.__name__}")

        # Call the tool exactly once
        return func(args)
    