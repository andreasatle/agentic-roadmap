"""
Iteration 5 main (manual tools).

Runs the Supervisor-controlled agent loop using a handcrafted compute tool (no OpenAI function calling).
You should see:
- occasional retries if an agent emits bad JSON
- occasional REJECT leading to Worker retry
- tool executions logged via agentic.compute
- but NO crashes and NO silent corruption.
"""

from dotenv import load_dotenv
from openai import OpenAI

from .agents import make_planner, make_worker, make_critic
from .supervisor import Supervisor
from .tools import Tool
from .compute import compute

load_dotenv(override=True)

client = OpenAI()

MODEL = "gpt-4o"  # keep consistent with your earlier iterations

planner = make_planner(client, MODEL)
worker = make_worker(client, MODEL)
critic = make_critic(client, MODEL)

supervisor = Supervisor(
    planner=planner, 
    worker=worker, 
    critic=critic, 
    max_retries=3, 
    max_loops=5,
    tools={
        "compute": Tool("compute", compute)
    }
)

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
