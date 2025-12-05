# Iteration 8 — Ensemble-Ready Dispatcher With Strict Tool Constraints

## Intent
Evolve the agent pipeline toward **ensemble-compatible workers** while enforcing:
- **Maximal constraints by default**
- **Zero workspace or repository mutation unless explicitly task-authorized**
- **Strict validation of all inbound and outbound payloads**
- **Supervisor-owned tool execution via a tool registry**
- **No implicit task inference from raw code or repository files**
- **No side effects from tools unless granted by a validated task object**

## What the code now shows
The project implements a clean three-agent pipeline:

1. **Planner** → emits a single `Task` (arithmetic op + operands)  
2. **Worker** → returns either:
   - a numeric `result`, or
   - a `tool_request` asking the Supervisor to invoke the arithmetic tool  
3. **Critic** → judges the worker output, returning `ACCEPT` or `REJECT`, and enforces feedback only on reject

All logic is **gated by Supervisor dispatch**, not by the completion model itself.

### Strict I/O validation observed
- `WorkerOutput.exactly_one_branch()` validates that exactly **one** branch is active (`result` *or* `tool_request`). 
- `Decision.require_feedback_on_reject()` enforces non-empty feedback only when decision is `REJECT`. 
- `ToolRegistry.call()` validates tool existence and the argument type, then executes the tool **exactly once**, with **no branching in the registry layer**. 
- `AgentDispatcher` implements bounded retries with JSON schema validation at the boundary for all agents (`plan`, `work`, `critique`). 

### Supervisor controls tool execution
The Supervisor owns the execution of deterministic tools through the registry, feeding results back into the Worker input without allowing pollution. 

## Ensemble readiness (no ensembling implemented **yet** — but the boundary supports it)
This iteration sets up the **structural preconditions** for adding ensembling in later iterations:

- Multiple Workers can be added behind the same dispatcher without modifying tool interfaces.
- The pipeline already isolates:
  - planning (user),
  - dispatch (Supervisor),
  - generation (Worker),
  - verification (Critic),
  - and execution (tool_registry)  
- This creates the **correct insertion point** for Worker ensembles later (e.g., majority voting or best-of-k), without altering contracts or polluting state.

**Important correction to your sentiment:**
> This step prepares the **interfaces and dispatching semantics** needed to integrate Worker ensembles professionally *later*, but no ensemble logic is currently active in the code. The smell you reject comes from unconstrained file mutation – that is now structurally prevented by boundary validation.

## Status
Iteration 8 achieves:
✔ vendor-neutral agents  
✔ deterministic tool isolation  
✔ strict boundary validation  
✔ write-nothing-unless-called semantics  
✔ scalable dispatcher suitable for future Worker ensembles  

**No more implicit repo mutations. No more nonsense files.**
