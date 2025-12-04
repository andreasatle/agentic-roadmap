from __future__ import annotations
from dataclasses import dataclass

from .schemas import WorkerInput, WorkerOutput, CriticInput
from .tool_registry import ToolRegistry
from .logging_config import get_logger
from .agent_dispatcher import AgentDispatcher

logger = get_logger("agentic.supervisor")


@dataclass
class Supervisor:
    dispatcher: AgentDispatcher
    tool_registry: ToolRegistry
    max_loops: int = 5

    def __call__(self) -> dict:
        """Planner → Worker → Critic loop, bounded, scalable."""
        planner_output = self.dispatcher.plan()

        # Initial WorkerInput
        worker_input = WorkerInput(task=planner_output)
        for iter in range(1, self.max_loops + 1):
            worker_output = self.dispatcher.work(worker_input)

            # Route on exactly one active branch
            match worker_output:

                # ----- Tool branch → call registry → reinject into worker input
                case WorkerOutput(tool_request=request) if request is not None:
                    # Guard: tool args should match the originating plan
                    if request.args.model_dump() != planner_output.model_dump():
                        raise RuntimeError("Tool args do not match plan")

                    # Call the registry exactly once
                    tool_result = self.tool_registry.call(request.tool_name, request.args)

                    # Rebuild next WorkerInput using registry output (Result)
                    worker_input = WorkerInput(
                        task=planner_output,
                        feedback="tool result applied",
                        tool_result=tool_result,
                    )

                # ----- Result branch → send numeric Result to critic
                case WorkerOutput(result=result) if result is not None:
                    critic_input = CriticInput(plan=planner_output, worker_answer=result)
                    critic_output = self.dispatcher.critique(critic_input)

                    # Act on critic signal
                    match critic_output.decision:
                        case "ACCEPT":
                            logger.info(f"[supervisor] ACCEPT on {iter}")
                            return {
                                "plan": planner_output,
                                "result": result,
                                "decision": critic_output,
                                "loops_used": iter,
                            }
                        case "REJECT":
                            logger.info(f"[supervisor] REJECT on {iter}")
                            # Reinject feedback into next worker input, keep tool_result if present
                            worker_input = WorkerInput(
                                task=planner_output,
                                previous_result=result,
                                feedback=critic_output.feedback,
                                tool_result=worker_input.tool_result,
                            )
                # ----- Safety fallback
                case _:
                    raise RuntimeError("WorkerOutput violated 'exactly one branch' invariant")

        raise RuntimeError("Supervisor exited without ACCEPT.")
