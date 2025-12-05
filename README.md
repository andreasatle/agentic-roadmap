# Agentic Framework (Current State)

## Overview
A small, domain-agnostic agentic framework with three LLM agents (Planner, Worker, Critic), a supervisor that orchestrates them, and a tool registry for deterministic functions. The framework is generic; domains bind their own task/result types and agent prompts.

## Architecture
- Framework (generic, no domain coupling):
  - `schemas.py`: Generic Pydantic models (`PlannerInput/Output`, `WorkerInput/Output`, `CriticInput`, `Decision`, `ToolRequest`, `ConstrainedXOROutput`).
  - `protocols.py`: Agent and tool protocols.
  - `agents.py`: Generic LLM Agent wrapper.
  - `agent_dispatcher.py`: Safe agent caller with retries and JSON validation.
  - `tool_registry.py`: Name → tool lookup and invocation with type checking.
  - `supervisor.py`: Planner → Worker → Critic loop, executes tools via registry.
  - `logging_config.py`: Logger setup.
- Domains:
  - `problem/arithmetic`: `Task`, `Result`, agent factories, dispatcher factory, tool registry (compute), prompts for arithmetic.
  - `problem/sentiment`: `Task`, `Result`, agent factories, dispatcher factory, empty tool registry, prompts for sentiment classification.

## How it runs
1) `main.py` imports a domain’s factories (`make_agent_dispatcher`, `make_tool_registry`).
2) Builds the dispatcher (planner, worker, critic) and a tool registry.
3) Supervisor loops:
   - Planner emits a `Task`.
   - Worker either returns a `result` or a `tool_request`.
   - On `tool_request`, supervisor calls the registry, feeds the result back to Worker.
   - On `result`, Critic decides ACCEPT/REJECT. Reject reinjects feedback; Accept returns.

## Switching domains
Edit `src/main.py` import block to choose one:
- Arithmetic: `from .problem.arithmetic import make_agent_dispatcher, make_tool_registry`
- Sentiment: `from .problem.sentiment import make_agent_dispatcher, make_tool_registry`

## Run the demo
```
uv run python -m src.main
```
Requires OpenAI credentials (uses `gpt-4.1-mini` by default). No network → demo will fail to call the API.

## Key files
- Framework: `src/schemas.py`, `src/protocols.py`, `src/agents.py`, `src/agent_dispatcher.py`, `src/supervisor.py`, `src/tool_registry.py`
- Arithmetic domain: `src/problem/arithmetic/`
- Sentiment domain: `src/problem/sentiment/`

