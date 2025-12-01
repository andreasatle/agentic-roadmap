"""
Iteration 3 main.

Runs the Supervisor-controlled agent loop.
You should see:
- occasional retries if an agent emits bad JSON
- occasional REJECT leading to Worker retry
- but NO crashes and NO silent corruption.

This is your first robust agent system.
"""

from dotenv import load_dotenv
from openai import OpenAI

from .agents import make_planner, make_worker, make_critic
from .supervisor import Supervisor

load_dotenv(override=True)

client = OpenAI()

MODEL = "gpt-4o"  # keep consistent with your earlier iterations

planner = make_planner(client, MODEL)
worker = make_worker(client, MODEL)
critic = make_critic(client, MODEL)

supervisor = Supervisor(planner=planner, worker=worker, critic=critic, max_retries=3, max_loops=5)

for i in range(5):
    record = supervisor.run_once()
    plan = record["plan"]
    result = record["result"]
    decision = record["decision"]
    loops_used = record["loops_used"]

    print(
        f"Run {i+1}:\n"
        f"  Plan: {plan.model_dump()}\n"
        f"  Result: {result.model_dump()}\n"
        f"  Decision: {decision.model_dump()}\n"
        f"  Loops used: {loops_used}\n"
        f"{'-'*40}"
    )
