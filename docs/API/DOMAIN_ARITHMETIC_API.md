# **DOMAIN_ARITHMETIC_API.md**

**Authoritative Canonical API for Arithmetic Domain**

---

## 1. Scope and Closure

This document defines the **normative API, contracts, and execution semantics** of the **Arithmetic domain** (`src/experiments/arithmetic`).

* This document is **authoritative** for the provided snapshot only.
* Any behavior not specified here is **undefined**.
* Any code that deviates from this document is **incorrect**.

### Semantic Closure Status

✅ **Semantically closed with respect to domain behavior**, under the explicit assumption that:

* `agentic` core APIs behave exactly as specified by their own authoritative API.
* No additional domain state or hidden side channels exist.

No missing files are required to understand or execute the Arithmetic domain correctly.

---

## 2. Domain Purpose

The Arithmetic domain is a **minimal, stateless reference domain** intended to demonstrate:

* Correct integration with the Agentic execution engine
* Worker capability routing
* Deterministic computation
* Tool invocation mechanics
* Critic-based correctness enforcement

It is intentionally simple and stable.

---

## 3. Core Domain Types

### 3.1 ArithmeticTask

```python
class ArithmeticTask:
    op: Literal["ADD", "SUB", "MUL"]
    a: int
    b: int
```

**Invariants**

* `op` MUST be one of `ADD`, `SUB`, `MUL`.
* `a` and `b` MUST be integers.
* The task is immutable once submitted to execution.

---

### 3.2 ArithmeticResult

```python
class ArithmeticResult:
    value: int
```

Represents the numeric result of the arithmetic operation.

---

### 3.3 Tool Argument Types

```python
class AddArgs: a: int; b: int
class SubArgs: a: int; b: int
class MulArgs: a: int; b: int
```

These types define the **only valid argument schemas** for arithmetic tools.

---

## 4. Worker Model

### 4.1 Workers and Capabilities

The domain defines **exactly two workers** with disjoint capabilities:

| Worker ID       | Supported Ops |
| --------------- | ------------- |
| `worker_addsub` | ADD, SUB      |
| `worker_mul`    | MUL           |

This mapping is **canonical** and MUST NOT be violated.

---

### 4.2 WorkerInput / WorkerOutput

```python
ArithmeticWorkerInput = WorkerInput[ArithmeticTask, ArithmeticResult]
ArithmeticWorkerOutput = WorkerOutput[ArithmeticResult]
```

**WorkerOutput Invariant (XOR)**

* Exactly one of:

  * `result`
  * `tool_request`
* MUST be present.
* Any violation is a schema error.

---

### 4.3 Worker Semantics

* Workers MUST compute supported operations **directly**.
* Workers MUST NOT compute unsupported operations.
* Workers MUST NOT execute tools themselves.
* On unsupported ops, workers MAY emit a `tool_request` or an error signal via schema-compliant output.

---

## 5. Planner

### 5.1 Planner Input / Output

```python
class ArithmeticPlannerInput:
    task: ArithmeticTask
```

```python
ArithmeticPlannerOutput:
    task: ArithmeticTask
    worker_id: Literal["worker_addsub", "worker_mul"]
```

---

### 5.2 Planner Routing Invariants

* `ADD` / `SUB` → MUST route to `worker_addsub`
* `MUL` → MUST route to `worker_mul`
* Any other routing is invalid.

The planner MUST always emit a task identical to the input task.

---

## 6. Critic

### 6.1 Critic Input / Output

```python
class ArithmeticCriticInput:
    plan: ArithmeticTask
    worker_id: str
    worker_answer: ArithmeticResult | None
```

```python
ArithmeticCriticOutput = Decision
```

---

### 6.2 Critic Invariants

The critic MUST enforce **both**:

1. **Correct Routing**

   * The worker used MUST support the operation in `plan.op`.

2. **Correct Computation**

   * If `worker_answer` is missing → REJECT
   * If `worker_answer.value` ≠ expected arithmetic result → REJECT

---

### 6.3 Decision Semantics

* `ACCEPT`

  * Only if routing AND math correctness are satisfied
  * Feedback MUST be `null`

* `REJECT`

  * Feedback MUST be present
  * Feedback MUST include:

    * `kind`
    * `message`

---

## 7. Tools

### 7.1 Tool Set

| Tool Name | Args Type | Semantics       |
| --------- | --------- | --------------- |
| `add`     | `AddArgs` | Returns `a + b` |
| `sub`     | `SubArgs` | Returns `a - b` |
| `mul`     | `MulArgs` | Returns `a * b` |

---

### 7.2 Tool Invariants

* Tools are deterministic.
* Tools MUST be invoked only through the ToolRegistry.
* Tool arguments MUST be validated against their schema.
* Tools execute exactly once per invocation.

---

## 8. Dispatcher Binding

```python
class ArithmeticDispatcher(AgentDispatcher[
    ArithmeticTask,
    ArithmeticResult,
    Decision
])
```

The Arithmetic domain binds Agentic generics as follows:

* **Task** → `ArithmeticTask`
* **Result** → `ArithmeticResult`
* **Decision** → `Decision`

No additional dispatcher behavior is introduced.

---

## 9. Public Domain API

### 9.1 Domain Entry Point

```python
def run(
    task: ArithmeticTask,
    *,
    dispatcher: ArithmeticDispatcher,
    tool_registry: ToolRegistry,
) -> ControllerResponse
```

**Semantics**

* Executes exactly one arithmetic task.
* Delegates execution entirely to the Agentic Controller.
* Returns a single immutable execution result.

---

## 10. Execution Semantics (End-to-End)

1. Input task is provided to `run(...)`
2. Controller performs:

   * PLAN → select worker
   * WORK → compute or request tool
   * (optional TOOL → WORK)
   * CRITIC → validate routing and math
   * END
3. Execution terminates after one pass.
4. No retries beyond AgentDispatcher retry semantics.
5. No domain state is persisted.

---

## 11. Authority Boundaries

### Domain Owns

* Task semantics
* Worker capability definitions
* Arithmetic correctness
* Tool definitions

### Domain Does NOT Own

* Execution loops
* Retry policy
* Workflow control
* State persistence
* UI or CLI behavior

---

## 12. Explicit Non-Features

The Arithmetic domain does **not**:

* Maintain domain state
* Perform multi-step workflows
* Retry tasks
* Mutate inputs
* Support non-integer arithmetic
* Support operations beyond ADD / SUB / MUL

---

## 13. Canonical Status

This document is **canonized** for the Arithmetic domain.

* It serves as the reference implementation contract.
* It may be used as a template for future domains.
* Any extension requires a new authoritative API document.

**End of DOMAIN_ARITHMETIC_API.md**
