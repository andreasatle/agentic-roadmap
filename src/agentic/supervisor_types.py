from enum import Enum, auto

class SupervisorState(Enum):
    PLAN = auto()
    WORK = auto()
    TOOL = auto()
    CRITIC = auto()
    END = auto()

class ContextKey(Enum):
    PLAN = auto()
    WORKER_INPUT = auto()
    WORKER_RESULT = auto()
    WORKER_OUTPUT = auto()
    TOOL_REQUEST = auto()
    TOOL_RESULT = auto()
    CRITIC_INPUT = auto()
    DECISION = auto()
    FEEDBACK = auto()
    LOOPS_USED = auto()
    FINAL_RESULT = auto()
    FINAL_OUTPUT = auto()
    TRACE = auto()
