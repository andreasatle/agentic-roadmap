# Iteration 4 — REASONING AGENTS (Hidden Scratchpads + JSON Extraction)

## **Goal**

Transition from “deterministic JSON-only agents” (Iteration 3) to agents that can:

* **Think privately** (scratchpad, chain-of-thought)
* **Reason before acting**
* **Self-correct across retries**
* **Still output strict JSON** as the *only* visible output

Iteration 4 lifts the restriction that prevented Workers and Critics from correcting themselves. We allow internal reasoning, but enforce that the final line is **pure JSON**, validated strictly by the Supervisor.

This dramatically improves reliability while maintaining full safety and determinism at the Supervisor level.

## **Why this iteration is needed**

Iteration 3 agents are:

* deterministic
* JSON-only
* schema-constrained
* but **non-reasoning**

This caused a fundamental limitation:

### ✔ If the Worker makes a rare mistake on a particular problem

it will **repeat the same mistake forever**, because:

* it has no internal reasoning
* retries are identical
* temperature=0.0 produces identical faulty outputs

In other words:

> **Iteration 3 agents cannot fix their own mistakes.**

Iteration 4 solves this *without* adding tools yet.

## **What changes in Iteration 4**

### **1. Hidden scratchpad reasoning**

Agents are allowed to produce *internal thought* before JSON:

```
Let me think…
14 * 7 = 98
{"result": 98}
```

The Supervisor extracts only the JSON substring.

### **2. JSON extraction in Supervisor**

We add a helper:

* Find the **last** `{ ... }`
* Validate only that portion
* Ignore anything before it

This enables:

* visible reasoning (for us)
* hidden reasoning (for the system)
* safe structured output

### **3. Self-correcting retries**

Since the Worker now reasons differently each time (even with temp=0), retries can recover from mistakes:

* First try: wrong
* Second try: correct
* Result accepted

Retries become meaningful.

### **4. Critic can reason too**

The Critic can:

* compute expected result
* compare
* reason about correctness
* decide ACCEPT or REJECT

Much more reliable than deterministic 1-shot JSON.

### **5. Prompts enforce dual-output pattern**

Agents must follow:

**Step 1:** Think privately
**Step 2:** Output ONLY JSON on the final line

This is crucial.

## **Prompt pattern introduced**

All Iteration 4 prompts adopt this invariant:

```
THINK STEP:
You MUST think step-by-step about the answer.
Do NOT reveal this reasoning in the final output.

FINAL OUTPUT:
On the LAST line, output ONLY valid JSON matching the schema.
```

This becomes the foundation for later tool-use (Iteration 5).

## **Supervisor responsibilities (upgraded)**

Supervisor now:

1. Calls agent with user_input
2. Receives mixed LLM output (reasoning + JSON)
3. Extracts JSON
4. Validates via Pydantic
5. Retries on:

   * malformed reasoning
   * malformed JSON
   * schema mismatch
6. Handles loop logic
7. Logs everything

The Supervisor remains the *trusted* brain; agents remain untrusted modules.

## **What this gives us**

* Agents that think but cannot leak chain-of-thought
* Self-correcting behavior
* Stable reliability without tools
* Deterministic control with non-deterministic reasoning
* Safe, typed, validated multi-agent loops
* Agents that feel “intelligent” but remain constrained

Iteration 4 is the turning point:
The system moves from “LLM as a deterministic JSON formatter” →
to “LLM as a reasoning unit with controlled output.”

## **Limitations (intended)**

Iteration 4 **does not** provide ground truth.
Worker and Critic can still be wrong.

This is by design.

### Grounding comes in Iteration 5 (Tools)

Where:

* Python or symbolic executors compute truth
* LLMs orchestrate computation

## **Example Flow (Iteration 4)**

Planner (scratchpad)

```
Let's generate a task.
I'll pick SUB and numbers 14 and 7.
{"op": "SUB", "a": 14, "b": 7}
```

Worker (scratchpad)

```
Compute 14 - 7 = 7.
{"result": 7}
```

Critic (scratchpad)

```
Expected: 14 - 7 = 7.
Matches result.
{"decision": "ACCEPT"}
```

Supervisor:

* extracts JSON from each
* validates schemas
* accepts task

This demonstrates the new pattern.

## **What comes next (Iteration 5 Preview)**

Iteration 5 introduces:

* Tool use (Python execution)
* Grounded correctness
* Deterministic Worker
* Deterministic Critic
* LLM → Tool → LLM loops

Iteration 4 is the final LLM-only iteration before grounding truth.

## **Summary**

Iteration 4 adds:

* Hidden reasoning
* Dual-output pattern
* JSON extraction
* Retry-based self-correction
* More intelligent behavior
* Safer Supervisor orchestration

Iteration 3 gave you structure.
**Iteration 4 gives your agents minds.**
Iteration 5 will give them *reality*.

