from typing import Any, Callable
from dataclasses import dataclass

@dataclass
class Tool:
    name: str
    func: Callable[..., Any]

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self.func(*args, **kwargs)