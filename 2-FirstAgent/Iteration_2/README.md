
# ITERATION 2 — STRUCTURED AGENT LOOP (JSON + PLACEHOLDERS)

## Goal:
Transition from natural-language prompts (Iteration 1) to *structured*
agent communication using JSON templates and placeholder substitution.
This removes ambiguity, eliminates drift, and prepares us for automated
parsing, retry logic, and a Supervisor in Iteration 3.

## Why we do this:
LLMs are unreliable when given free-form language. They:
- copy examples literally (anchoring problem)
- mix structure with explanation
- occasionally hallucinate fields
- forget formatting rules
- produce inconsistent outputs across calls

## Structured agent prompts fix this by:
- enforcing a single OUTPUT FORMAT TEMPLATE
- defining placeholder variables ($OP, $A, $B, $Z)
- requiring explicit replacement of placeholders
- forbidding natural language
- requiring "ONLY valid JSON"
- separating Planner, Worker, and Critic roles

## What changes from Iteration 1:
1. Planner now outputs JSON, not English.
2. Worker reads JSON and produces JSON.
3. Critic validates JSON.
4. Randomness is explicitly defined (uniform).
5. All roles share a strict, machine-readable schema.
6. Prompts forbid explanation, comments, or extra text.
7. Placeholder substitution ensures full determinism in structure.

## What this gives us:
- Deterministic structure for parsing
- Varied arithmetic tasks (Planner diversity)
- Stable numeric computation (Worker determinism)
- Reliable correctness checking (Critic determinism)
- No accidental natural-language leakage
- No malformed JSON or drift during the loop

This is the first iteration where the agents become
"machine-operable" rather than "chat-operable", and it
sets the foundation for Iteration 3:
Supervisor + JSON parsing + Retry logic.
