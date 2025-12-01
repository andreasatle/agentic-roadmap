from .logging_config import get_logger

logger = get_logger("agentic.compute")


def compute(op: str, a: int, b: int) -> int:
    logger.info(f"TOOL: compute with arg: op={op}, a={a}, b={b}")
    match op:
        case "ADD":
            return a + b
        case "SUB":
            return a - b
        case "MUL":
            return a * b
        case _:
            raise ValueError(f"invalid op: {op}")
