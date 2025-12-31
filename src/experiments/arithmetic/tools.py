
from experiments.arithmetic.types import AddArgs, SubArgs, MulArgs, ArithmeticResult


def add(args: AddArgs) -> ArithmeticResult:
    """Deterministic addition tool."""
    return ArithmeticResult(value=args.a + args.b)


def sub(args: SubArgs) -> ArithmeticResult:
    """Deterministic subtraction tool."""
    return ArithmeticResult(value=args.a - args.b)


def mul(args: MulArgs) -> ArithmeticResult:
    """Deterministic multiplication tool."""
    return ArithmeticResult(value=args.a * args.b)
