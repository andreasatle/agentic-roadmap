# ITERATION 3 — SUPERVISOR + JSON PARSING + RETRY LOGIC + TYPED CONTRACTS

## Goal:
Move from "structured JSON prompts" (Iteration 2) to a *machine-verifiable,
schema-enforced* agent pipeline. This removes the remaining ambiguity by
adding:

1. A Supervisor that orchestrates Planner → Worker → Critic.
2. Pydantic schemas to type every agent input/output.
3. Automatic JSON parsing and validation.
4. Bounded retry logic for malformed or schema-violating outputs.
5. Deterministic, role-separated agents using JSON-only responses.

## Why we do this:
Even with strict placeholder templates (Iteration 2), LLMs still:
- occasionally output malformed JSON,
- hallucinate fields or values,
- omit required keys,
- or mix stray text into outputs.

These failures must NOT crash the system.
Instead, the system must:
- catch invalid JSON,
- validate against a schema (Plan, Result, Decision),
- retry safely, and
- keep the agent loop deterministic.

## What changes from Iteration 2:
1. **Supervisor** becomes the trusted control-plane.
2. Agents are now *untrusted* and treated as stochastic components.
3. Every agent message is validated via Pydantic v2.
4. Retries are explicit and bounded (no infinite loops).
5. Worker/Critic loops are bounded (max_loops).
6. Each agent has a strict typed I/O schema:
   - PlannerInput / PlannerOutput
   - WorkerInput / WorkerOutput
   - CriticInput / CriticOutput
7. JSON-only communication is enforced through the OpenAI API.
8. Logging provides visibility into every step.

## What this gives us:
- Strong safety against malformed LLM output.
- Deterministic orchestration with predictable behavior.
- Fully machine-verifiable agent communication.
- A robust pipeline where errors cause retries, not crashes.
- Separation of concerns:
    Supervisor = control
    Agents     = untrusted compute modules

## Why this iteration matters:
This is the iteration where the architecture becomes *real software*
instead of a clever prompt chain.

Iteration 3 is the first version that is:
- structured,
- validated,
- typed,
- logged,
- fault-tolerant.

## It sets the stage for Iteration 4:
Hidden chain-of-thought + JSON extraction + self-correcting agents.

Iteration 3 establishes the infrastructure that Iteration 4 builds on.

