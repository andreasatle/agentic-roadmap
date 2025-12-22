# **AGENTIC_API.md**

**Authoritative Canonical API for Agentic Core**

---

## 1. Scope and Authority

This document defines the **normative API and execution semantics** of the **Agentic Core** (`src/agentic`).

* This document is **authoritative**.
* Any code that contradicts this document is **incorrect**.
* Any behavior not specified here is **undefined** and MUST NOT be relied upon.
* This document is sufficient for correct reasoning **without access to implementation code**.

This API governs **domain-agnostic execution only**. Domain logic, workflows, and UI behavior are explicitly out of scope.

---

## 2. Execution Model (Global Invariants)

### 2.1 Atomic Execution

* All controllers execute **exactly one atomic execution attempt** per call.
* No controller performs implicit looping or workflow advancement.
* Retry behavior is bounded and occurs **only at schema-validation boundaries**.

### 2.2 Determinism

* All observable outputs MUST be fully derivable from:

  * input payloads
  * agent responses
  * registered tools
* Hidden mutable state is forbidden at the controller layer.

### 2.3 Trust Boundaries

* **Controllers are trusted.**
* **Agents are untrusted.**
* All agent outputs MUST be schema-validated before use.

---

## 3. Core Actors

### 3.1 Controller

**Role:** Pure execution engine for a single task.

#### Contract

* MUST execute exactly one task per request.
* MUST follow the fixed FSM:

```
PLAN → WORK → (optional TOOL → WORK) → CRITIC → END
```

* MUST NOT:

  * create tasks
  * loop for progress
  * mutate domain state
  * manage workflows
* MUST return a single immutable response.

#### Request

```python
class ControllerRequest:
    domain: ControllerDomainInput  # exactly one task
```

#### Response

```python
class ControllerResponse:
    task: Any
    worker_id: str
    worker_output: Any | None
    critic_decision: Any | None
    trace: list[dict] | None
```

---

### 3.2 AnalysisController

**Role:** Planner-only execution.

#### Contract

* Executes exactly one planning step.
* MUST NOT invoke workers, critics, or tools.
* Planner output is final and authoritative.

#### Request

```python
class AnalysisControllerRequest:
    planner_input: BaseModel
```

#### Response

```python
class AnalysisControllerResponse:
    planner_input: Any
    plan: Any
    trace: list[dict] | None
```

---

## 4. AgentDispatcher

**Role:** Validated, bounded invocation of LLM agents.

### 4.1 Retry Semantics

* Retries occur **only** when output fails schema validation.
* Retries are bounded by `max_retries`.
* Raw agent output is never trusted without validation.

### 4.2 Interface

```python
class AgentDispatcher:
    planner: AgentProtocol
    workers: dict[str, AgentProtocol]
    critic: AgentProtocol
```

### 4.3 Guarantees

* On success, returns a typed `AgentCallResult`.
* On failure, raises after retry exhaustion.
* Dispatcher never mutates domain state.

---

## 5. Agent Protocols

### 5.1 AgentProtocol

```python
class AgentProtocol(Protocol):
    name: str
    input_schema: type[BaseModel]
    output_schema: type[BaseModel]
    def __call__(self, input_json: str) -> str
```

* Agents MUST accept JSON input.
* Agents MUST return JSON output.
* Agents are not trusted to be correct or well-behaved.

### 5.2 Provider Adapters

* OpenAIAgent and ClaudeAgent are **non-normative adapters**.
* Provider-specific behavior is explicitly out of scope.

---

## 6. Planner / Worker / Critic Schemas

### 6.1 Planner

```python
class PlannerInput[T, R]:
    feedback: Feedback | None
    previous_task: T | None
    previous_worker_id: str | None
    random_seed: str | None
    project_state: dict | None
```

```python
class PlannerOutput[T]:
    task: T
    worker_id: str
```

### 6.2 Worker

```python
class WorkerInput[T, R]:
    task: T
    previous_result: R | None
    feedback: Feedback | None
    tool_result: R | None
    project_state: dict | None
```

```python
class WorkerOutput[R]:
    result: R | None
    tool_request: ToolRequest | None
```

#### XOR Invariant

* Exactly **one** of `result` or `tool_request` MUST be set.
* Any violation is a schema error.

### 6.3 Critic

```python
class CriticInput[T, R]:
    plan: T
    worker_answer: R
    project_state: dict | None
```

```python
class Decision:
    decision: Literal["ACCEPT", "REJECT"]
    feedback: Feedback | None
```

#### Invariant

* `REJECT` decisions MUST include feedback.
* `ACCEPT` decisions MAY omit feedback.

---

## 7. Tools

### 7.1 ToolRegistry

**Role:** Deterministic side-effect execution.

#### Contract

* Tools MUST be registered explicitly.
* Arguments MUST be validated by type before execution.
* Each tool invocation occurs **exactly once**.

```python
class ToolRegistry:
    def register(name, description, func, arg_type)
    def get(name)
    def call(name, args)
```

---

## 8. Tracing and Observability

* Controllers produce structured execution traces.
* Trace content is informational only.
* Trace shape is stable but not a behavioral dependency.

---

## 9. Extension Points

### Allowed

* Domain-defined task types
* Domain-defined schemas
* Domain-defined planners, workers, critics
* Tool registration

### Forbidden

* Domain-specific logic in controllers
* Workflow orchestration at Agentic level
* Implicit recursion or looping
* State mutation inside controllers

---

## 10. Explicit Non-Features

The Agentic Core **does not**:

* Manage workflows
* Perform multi-step planning loops
* Store or evolve domain state
* Retry tools
* Perform inference outside schemas
* Contain UI, CLI, or app logic

---

## 11. Canonical Status

This document is **canonized**.

* All downstream domains and apps MUST conform.
* Any deviation requires explicit modification of this document.
* This API is stable across refactors and implementations.

**End of AGENTIC_API.md**
