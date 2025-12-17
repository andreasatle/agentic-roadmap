from pydantic import BaseModel, Field


class ContentStore(BaseModel):
    by_node_id: dict[str, str] = Field(default_factory=dict)

