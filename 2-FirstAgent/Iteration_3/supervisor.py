"""
Iteration 3 Supervisor (Option B: class-based with clean control).

Responsibilities:
1. Call agents.
2. Validate JSON + schema using Pydantic.
3. Retry boundedly on failure.
4. Loop boundedly until ACCEPT.

This is the *control plane*.
Agents are untrusted. The Supervisor is trusted.
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

    def safe_call(self, agent: AgentProtocol, input: AgentInput) -> AgentOutput:
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
                print(f"[safe_call] retry {attempt}/{self.max_retries} — invalid {agent.output_schema.__name__}: {e.errors()}")
        raise RuntimeError(f"Agent failed schema {agent.output_schema.__name__} after {self.max_retries} retries. Last error: {last_err}")

    def run_once(self) -> dict:
        """
        One full Plan -> Act -> Check loop with bounded refinement.
        Returns a structured record of the accepted run.
        """
        planner_input = PlannerInput()
        planner_output: PlannerOutput = self.safe_call(self.planner, planner_input)

        for loop_idx in range(1, self.max_loops + 1):
            worker_input: WorkerInput = WorkerInput(**planner_output.model_dump())
            worker_output: WorkerOutput = self.safe_call(self.worker, worker_input)
            critic_input: CriticInput = CriticInput(**worker_input.model_dump(), **worker_output.model_dump())
            critic_output: CriticOutput = self.safe_call(self.critic, critic_input)

            if critic_output.decision == "ACCEPT":
                return {
                    "plan": planner_output,
                    "result": worker_output,
                    "decision": critic_output,
                    "loops_used": loop_idx,
                }

            print(f"[supervisor] loop {loop_idx}/{self.max_loops} — REJECT, retrying Worker")

        raise RuntimeError(f"Supervisor hit max_loops={self.max_loops} without ACCEPT.")
