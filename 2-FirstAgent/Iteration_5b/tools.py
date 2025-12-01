from pydantic import BaseModel
from typing import Any, TypeVar

SchemaModel = TypeVar("SchemaModel", bound=BaseModel)

def make_tool_from_schema(
    name: str,
    description: str,
    schema_model: type[SchemaModel],
) -> dict[str, Any]:
    """Generate an OpenAI tool definition from a Pydantic schema model."""
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": schema_model.model_json_schema(),
        },
    }
