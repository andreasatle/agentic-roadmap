"""
Iteration 5 Supervisor (class-based, OpenAI tools).

Responsibilities:
1. Call agents with strict JSON validation.
2. Retry boundedly on malformed output.
3. Loop boundedly until ACCEPT.

Tool execution happens inside the Worker via OpenAI function calling; Supervisor remains the control plane.
"""

from __future__ import annotations

from dataclasses import dataclass
from pydantic import ValidationError

from .schemas import (
    PlannerInput,
    PlannerOutput,
    WorkerInput,
    WorkerOutput,
    CriticInput,
    CriticOutput,
)

from .protocols import AgentProtocol, AgentInput, AgentOutput
from .logging_config import get_logger

logger = get_logger("agentic.supervisor")

@dataclass
class Supervisor:
    planner: AgentProtocol[PlannerInput, PlannerOutput]
    worker: AgentProtocol[WorkerInput, WorkerOutput]
    critic: AgentProtocol[CriticInput, CriticOutput]
    max_retries: int = 3
    max_loops: int = 5

    def safe_call(
        self, 
        agent: AgentProtocol[AgentInput, AgentOutput], 
        input: AgentInput
    ) -> AgentOutput:
        """
        Call an agent and validate its output against a Pydantic schema.
        Retries on malformed JSON or schema mismatch.
        """
        logger.debug(f"Calling agent {agent.name} with input: {input.model_dump()}")
        last_err: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            raw = agent(input.model_dump_json())
            logger.debug(f"Raw output from {agent.name}: {raw}")
            try:
                # Pydantic v2: validate from JSON string
                return agent.output_schema.model_validate_json(raw)
            except ValidationError as e:
                last_err = e
                logger.info(f"[safe_call] retry {attempt}/{self.max_retries} — invalid {agent.output_schema.__name__}: {e.errors()}")
        raise RuntimeError(f"Agent failed schema {agent.output_schema.__name__} after {self.max_retries} retries. Last error: {last_err}")

    def run_once(self) -> dict:
        """
        One full Plan -> Act -> Check loop with bounded refinement.
        Returns a structured record of the accepted run.
        """
        planner_input = PlannerInput()
        planner_output: PlannerOutput = self.safe_call(self.planner, planner_input)
        worker_input: WorkerInput = WorkerInput(task=planner_output)

        for loop_idx in range(1, self.max_loops + 1):
            worker_output: WorkerOutput = self.safe_call(self.worker, worker_input)

            # Branch: normal result -> send to Critic
            critic_input: CriticInput = CriticInput(
                plan=planner_output,
                worker_answer=worker_output.result,
            )
            critic_output: CriticOutput = self.safe_call(self.critic, critic_input)

            if critic_output.decision == "REJECT":
                worker_input = WorkerInput(
                    task=planner_output,
                    previous_result=worker_output.result,
                    feedback=critic_output.feedback,
                    tool_result=worker_input.tool_result,
                )
                logger.info(f"[supervisor] loop {loop_idx}/{self.max_loops} — REJECT, retrying Worker")
            elif critic_output.decision == "ACCEPT":
                return {
                    "plan": planner_output,
                    "result": worker_output,
                    "decision": critic_output,
                    "loops_used": loop_idx,
                }



        raise RuntimeError(f"Supervisor hit max_loops={self.max_loops} without ACCEPT.")
