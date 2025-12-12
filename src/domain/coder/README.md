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