
import json
from pathlib import Path
from typing import TypeVar, Type

from pydantic import BaseModel

Self = TypeVar("Self", bound="LoadSaveMixin")


class LoadSaveMixin(BaseModel):
    """
    Optional persistence mixin for stateful domain states.
    Allows:
        state = MyDomainState.load()
        state.save()
    """

    @classmethod
    def _state_path(cls) -> Path:
        domain = getattr(cls, "domain_name", cls.__name__).lower()
        root = Path(".agentic_state")
        root.mkdir(exist_ok=True)
        return root / f"{domain}.json"

    @classmethod
    def load(cls: Type[Self]) -> Self:
        path = cls._state_path()
        if not path.exists():
            return cls()
        data = json.loads(path.read_text())
        return cls.model_validate(data)

    def save(self) -> None:
        path = self.__class__._state_path()
        path.write_text(self.model_dump_json(indent=2))
