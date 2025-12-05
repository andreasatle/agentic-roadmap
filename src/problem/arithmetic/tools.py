from __future__ import annotations

from .types import Task, Result

def compute(args: Task) -> Result:
    """
    Deterministic arithmetic tool.
    """
    match args.op:
        case "ADD":
            value = args.a + args.b
        case "SUB":
            value = args.a - args.b
        case "MUL":
            value = args.a * args.b
        case _:
            raise ValueError(f"Unknown op: {args.op}")

    return Result(value=value)
