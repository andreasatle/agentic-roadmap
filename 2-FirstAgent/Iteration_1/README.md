# ITERATION 1 — SYMBOLIC DSL LOOP

## PURPOSE:
Iteration 1 is the foundation of agent engineering. Its goal is to stabilize the Planner → Worker → Critic loop by removing all natural-language ambiguity.

## WHY:
LLMs drift or make rare mistakes whenever they are asked to
interpret natural language, even very simple arithmetic tasks.
Phrases like:
    "Add 7 and 12"
    "Multiply 8 and 15"
trigger the model’s *semantic mode*, which involves grammar,
paraphrasing, and interpretation.
This leads to occasional failures, especially when the model 
tries to “help” by rephrasing the task or interpreting intent.

## THE FIX:
Use a SYMBOLIC DSL instead of English.
We force the Planner to output *dry, non-linguistic tokens*:
    ADD 7 12
    SUB 15 4
    MUL 8 20
These do NOT resemble English sentences. As a result, the LLM 
switches into *symbolic parsing mode* instead of language mode. 
The Worker and Critic behave deterministically.

## KEY LESSONS LEARNED:
1. Natural language is always unstable for inter-agent messages.
   Even tiny English-like patterns cause drift.
2. A symbolic DSL forces mechanical, predictable behavior.
   (Capital letters eliminate verb semantics like "Add".)
3. The instability was NOT in the logic; it was in the FORMAT.
4. Agents must communicate like machines, not humans.
5. Once the DSL was enforced, the loop ran correctly 5/5,
   and stability held across multiple iterations.

## WHAT THIS ITERATION ACHIEVES:
- A stable, repeatable 3-agent loop.
- Zero reliance on English semantics.
- A clean separation of roles.
- A deterministic communication format.

## NEXT STEPS:
In Iteration 2, we move from DSL tokens → structured JSON.
This will form the bridge to Pydantic schemas in Iteration 3.
