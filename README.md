# Root README.md

## AgenticRoadmap

This repository contains an experimental, **state-machine–driven agentic framework** built around a strict Planner–Worker–Critic (PWC) loop. The system is designed to explore how structured supervision, typed state, and explicit control flow can be used to build reliable multi-step LLM-driven programs.

### Core Principles

* **Supervisor-driven execution** (explicit state machine, no hidden loops)
* **Strict schemas everywhere** (Pydantic validation at boundaries)
* **Domain independence** (Supervisor has no domain knowledge)
* **Restartable, persistent state** (no infinite loops, no silent retries)

### Repository Structure

```
root/
├─ src/agentic/        # Supervisor, dispatcher, tool registry
├─ src/domain/         # Domain-specific planners/workers/critics
│  ├─ writer/
│  ├─ coder/
│  ├─ arithmetic/
│  └─ sentiment/
```

Each domain is a thin specialization layered on top of the same agentic core.

## agentic-document-from-text CLI

Pipeline (advisory where noted):
- Raw user text → text prompt refiner (advisory, semantic-preserving)
- Refined text → intent adapter → `IntentEnvelope` (advisory)
- Intent → document planner → writer + critic → markdown assembly

Flags:
- `--text`: inline raw user text (authoritative input).
- `--trace`: print advisory intent observation/audit; no behavioral impact.
- `--print-intent`: print parsed `IntentEnvelope` as YAML (advisory, read-only, non-authoritative) derived from `intent.model_dump()`, then continue execution normally.

Intent:
- Intent is the structured summary (`IntentEnvelope`) extracted from refined text.
- Printed in YAML for readability; not editable or accepted as input in this flow.
- Any intent shown is advisory only; downstream planning/writing remain unchanged by printing.

---

# src/agentic/README.md

## Agentic Core

The `agentic` package implements the **domain-agnostic execution engine**.

### Key Components

* **Supervisor**

  * Explicit state machine (PLAN → WORK → TOOL → CRITIC → END)
  * Enforces loop bounds and termination
  * Owns retry and acceptance logic

* **AgentDispatcher**

  * Handles agent invocation
  * Validates JSON output against schemas
  * Retries only at schema boundaries

* **ToolRegistry**

  * Strongly typed tool invocation
  * Enforces argument schemas

### Design Constraints

* Supervisor never mutates domain state directly
* No domain-specific branching
* No implicit recursion or infinite loops

This layer should remain stable while domains evolve.

---

# src/domain/writer/README.md

## Writer Domain

The Writer domain implements a **multi-section article generator** using the agentic framework.

### State Model

Writer is now stateless: it accepts a `WriterTask` and returns a `WriterResult`. Document structure, ordering, and persistence live outside the writer domain.

### Planner Responsibilities

* Select next section
* Decide operation (`draft` vs `refine`)
* Optionally emit `section_order`

### Worker Responsibilities

* Produce JSON-only output
* Merge text only in `refine` mode
* Never invent structure

### Critic Responsibilities

* Single-section validation only
* Reject empty output
* Accept everything else (MVP)

The Writer is designed to become **topic-agnostic** once prompt cleanup is complete.

---

# src/domain/coder/README.md

## Coder Domain

The Coder domain generates and refines code artifacts.

### Current State (Intentional)

* Uses a single `ProblemState`
* State currently mixes **context** and **content**

This is **known technical debt** and will be addressed in a future refactor by splitting:

* `CoderContextState`
* `CodebaseState` (or equivalent)

### Why It Exists

Coder was implemented earlier in the project before the context/content distinction was formalized. It remains functional but architecturally asymmetric by design.

---

# src/domain/arithmetic/README.md

## Arithmetic Domain

A minimal, stateless example domain.

### Characteristics

* Uses `ArithmeticContextState` (stateless)
* Demonstrates tool invocation and validation
* Useful as a reference for minimal domain integration

This domain is intentionally simple and stable.

---

# src/domain/sentiment/README.md

## Sentiment Domain

A lightweight sentiment-analysis example.

### Characteristics

* Stateless execution
* No persistent artifacts
* Demonstrates planner → worker → critic flow without content accumulation

Primarily used to validate Supervisor behavior under trivial state.

---

## Notes on Architecture

* `ContextState` names indicate **control and progression**, not payloads
* Content-heavy domains should separate content from context
* `isinstance` checks are temporary and tracked as explicit debt

The project favors **explicitness over cleverness** and **correctness over convenience**.

## License

This project is licensed under the MIT License.

The repository is public to encourage transparency, learning, and discussion.
Future commercial offerings (e.g. hosted services, enterprise features, or
integrations) may be developed separately and are not implied to be covered
by this license.
