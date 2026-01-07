# src/agentic/README.md

## Agentic Core

The `agentic` package implements the **domain-agnostic execution engine**.

### Key Components

* **Controller**

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

* Controller never mutates domain state directly
* No domain-specific branching
* No implicit recursion or infinite loops

This layer should remain stable while domains evolve.
