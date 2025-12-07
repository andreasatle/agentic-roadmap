# Agentic Framework

## Overview
A small, domain-agnostic agent framework with three LLM agents (Planner, Worker, Critic) coordinated by a finite-state Supervisor and a tool registry for deterministic functions. The framework is generic; domains bind their own task/result types, prompts, and tools.

## Architecture (framework)
- `agentic/schemas.py`: Generic Pydantic models (`PlannerInput/Output`, `WorkerInput/Output`, `CriticInput`, `Decision`, `ToolRequest`, `ConstrainedXOROutput`).
- `agentic/protocols.py`: Agent and tool protocols.
- `agentic/agents.py`: Thin OpenAI LLM wrapper with typed I/O.
- `agentic/agent_dispatcher.py`: Safe agent caller with retries and JSON validation; `plan` now accepts optional planner context.
- `agentic/supervisor_types.py`: FSM state enum + `SupervisorContext` (stores current/previous plan, planner feedback, worker inputs/outputs, trace).
- `agentic/supervisor.py`: PLAN → WORK → TOOL/CRITIC → END loop; CRITIC REJECT can route back to PLAN with planner_feedback, making the planner self-correct.
- `agentic/tool_registry.py`: Name → tool lookup and invocation with type checking.
- `agentic/logging_config.py`: Logger setup.

## Domains
- `agentic/problem/arithmetic`: Task/Result schemas, agent factories, dispatcher factory, tool registry (compute), prompts for arithmetic.
- `agentic/problem/sentiment`: Task/Result schemas, agent factories, dispatcher factory, empty tool registry, prompts for sentiment classification.

## Control flow
1. Planner produces a `PlannerOutput` (`task`, `worker_id`). On failures/critic rejection, planner receives `PlannerInput(feedback, previous_task, previous_worker_id)` for self-correction.
2. Worker runs on the chosen `worker_id`, returning either a `result` or `tool_request`.
3. TOOL: supervisor invokes the requested deterministic tool and feeds the `tool_result` back into Worker.
4. CRITIC judges `plan` + `worker_answer` as ACCEPT/REJECT. REJECT routes feedback to Worker or, when planning failed, back to Planner.
5. Supervisor records a trace of each transition and stops at END.

## Running the demo
```
uv run python -m agentic.main
```
Requires `OPENAI_API_KEY` (uses `gpt-4.1-mini` by default). Without network access, calls to the API will fail.

## Switching domains
Edit the import block in `agentic/main.py`:
- Arithmetic (default): `from agentic.problem.arithmetic import make_agent_dispatcher, make_tool_registry`
- Sentiment: `from agentic.problem.sentiment import make_agent_dispatcher, make_tool_registry`
