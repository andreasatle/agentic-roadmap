# **DOMAIN_SENTIMENT_API.md**

**Authoritative Canonical API for Sentiment Domain**

---

## 1. Scope and Closure

This document defines the **normative API, contracts, and execution semantics** of the **Sentiment domain** (`src/domain/sentiment`).

* This document is **authoritative** for the provided snapshot only.
* Anything not specified here is **undefined** and MUST NOT be inferred.
* If implementation code deviates from this document, the **code is wrong**.

### Semantic Closure Status

⚠️ **Conditionally semantically closed**

The domain is semantically closed **with respect to domain behavior**, under the explicit assumption that:

* The Agentic core (`Controller`, `AgentDispatcher`, schemas, retry semantics) behaves according to its own authoritative API.
* `_normalize_for_json` exists and behaves consistently with other domains, but **its definition is not included here**. Its behavior is therefore **opaque but non-authoritative**.

No additional sentiment-domain files are required for correct reasoning.

---

## 2. Domain Purpose

The Sentiment domain is a **stateless, single-pass sentiment classification domain** intended to:

* Validate the planner → worker → critic execution path
* Exercise Controller orchestration under trivial state
* Demonstrate correctness enforcement without tools or state accumulation

The domain does **not** attempt to optimize sentiment accuracy; it enforces **contractual correctness**, not model quality.

---

## 3. Core Domain Types

### 3.1 SentimentTask

```python
class SentimentTask:
    text: str            # max length 280
    target_sentiment: Literal["POSITIVE", "NEGATIVE", "NEUTRAL"]
```

**Invariants**

* `text` MUST be a non-empty string with length ≤ 280.
* `target_sentiment` MUST be one of `POSITIVE`, `NEGATIVE`, `NEUTRAL`.
* The task is immutable for the duration of execution.

---

### 3.2 Result

```python
class Result:
    sentiment: Literal["POSITIVE", "NEGATIVE", "NEUTRAL"]
```

Represents the Worker’s sentiment classification of `task.text`.

---

## 4. Planner

### 4.1 Planner Input / Output

```python
class SentimentPlannerInput:
    task: SentimentTask
    # additional fields allowed (extra="allow")
```

```python
SentimentPlannerOutput:
    task: SentimentTask
    worker_id: Literal["sentiment-worker"]
```

---

### 4.2 Planner Invariants

* The planner MUST emit exactly one `SentimentTask`.
* The planner MUST always assign `worker_id = "sentiment-worker"`.
* The planner MAY vary `text` and `target_sentiment` across runs.
* The planner MUST NOT emit any worker other than `"sentiment-worker"`.

---

### 4.3 Planner Semantics

* The planner’s responsibility is **task generation**, not classification.
* Feedback MAY be used to alter future tasks, but is never required.
* Absence of state MUST NOT cause planner failure.

---

## 5. Worker

### 5.1 Worker Input / Output

```python
SentimentWorkerInput = WorkerInput[SentimentTask, Result]
SentimentWorkerOutput = WorkerOutput[Result]
```

**WorkerOutput Invariant**

* Exactly one branch MUST be active.
* In this domain, only `result` is permitted.
* `tool_request` MUST NOT be used.

---

### 5.2 Worker Semantics

* The worker MUST classify sentiment based **only on `task.text`**.
* The worker MUST ignore `task.target_sentiment`.
* The worker MUST NOT request tools.
* The worker MUST emit exactly one sentiment label.

---

## 6. Critic

### 6.1 Critic Input / Output

```python
class SentimentCriticInput:
    plan: SentimentTask
    worker_answer: Result | None
    worker_id: str | None
```

```python
SentimentCriticOutput = Decision
```

---

### 6.2 Critic Invariants

The critic MUST enforce:

1. **Presence**

   * If `worker_answer` is missing or null → REJECT

2. **Match Against Target**

   * If `worker_answer.sentiment == plan.target_sentiment` → ACCEPT
   * Otherwise → REJECT

---

### 6.3 Decision Semantics

* **ACCEPT**

  * Feedback MUST be `null`

* **REJECT**

  * Feedback MUST be present
  * Feedback.kind MUST be one of:

    * `EMPTY_RESULT`
    * `MISMATCH`
    * `OTHER`
  * Feedback.message MUST be actionable for the planner

---

## 7. Tools

### Tool Model

* **No tools exist in this domain.**
* The ToolRegistry MUST be empty.
* Any attempt to invoke tools is invalid behavior.

---

## 8. Dispatcher Binding

```python
SentimentDispatcher = AgentDispatcher[
    SentimentTask,
    Result,
    Decision
]
```

The Sentiment domain binds Agentic generics as follows:

* **Task** → `SentimentTask`
* **Result** → `Result`
* **Decision** → `Decision`

No domain-specific dispatcher behavior is introduced.

---

## 9. Public Domain API

### 9.1 Entry Point

```python
def run(
    task: SentimentTask,
    *,
    dispatcher: SentimentDispatcher,
    tool_registry: ToolRegistry,
) -> ControllerResponse
```

**Semantics**

* Executes exactly one sentiment classification task.
* Delegates execution entirely to the Agentic Controller.
* Returns a single immutable execution result.
* Ignores tool_registry contents (must be empty).

---

## 10. Execution Semantics (End-to-End)

1. `SentimentTask` is provided to `run(...)`
2. Controller performs:

   * PLAN → generate task
   * WORK → classify sentiment
   * CRITIC → compare against target_sentiment
   * END
3. Execution is:

   * Single-pass
   * Non-iterative
   * Stateless
4. No retries beyond dispatcher retry rules.
5. No domain state is persisted.

---

## 11. Authority Boundaries

### Domain Owns

* Task semantics
* Sentiment labels
* Correctness judgment
* Worker behavior constraints

### Domain Does NOT Own

* Workflow control
* Retry strategy
* State persistence
* Tool execution
* Planner iteration loops
* UI / CLI behavior

---

## 12. Explicit Non-Features

The Sentiment domain explicitly does **not** support:

* Tools
* Multi-step reasoning
* Accumulated state
* Confidence scoring
* Partial or probabilistic outputs
* Multiple workers
* Worker routing logic
* Domain-side retries

---

## 13. Canonical Status

This document is **canonized** for the Sentiment domain.

* It defines the authoritative behavioral contract.
* It is sufficient for reasoning without code access.
* It serves as a minimal reference domain alongside Arithmetic.

**End of DOMAIN_SENTIMENT_API.md**
