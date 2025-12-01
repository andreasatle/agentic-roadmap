# **Iteration 5 — Tool-Use (Trusted Operations inside the Worker)**

Iteration 5 is the first *real* jump toward serious agentic systems.
In Iterations 1–4, the Worker computed everything **inside the LLM**, meaning:

* The LLM could hallucinate incorrect arithmetic.
* The Critic needed to catch errors.
* The Supervisor had to retry loops.
* We were fundamentally limited by the stochastic, unreliable nature of the model.

Iteration 5 changes the game:

> **The Worker stops “thinking” and starts *using a tool*.**

The Worker LLM now:

1. Parses the input (operation, operands, prior feedback).
2. Calls a **trusted Python function** to compute the true result.
3. Returns correct JSON deterministically.

This is the foundation for *real world* agentic systems:

* The LLM does planning / reasoning.
* The tools do the grounded, trustworthy work.

## **Why Iteration 5 Matters**

Before this iteration:

* Worker occasionally hallucinated results (e.g., `105` judged wrong, etc.)
* Critic had nondeterministic mistakes.
* Loops were wasted on correcting nonsense.

After this iteration:

* Arithmetic becomes **100% correct**.
* Feedback loops become **far more stable**.
* Supervisor’s retries are triggered only by JSON formatting errors.

This matches real agent architecture:

* LLM = high-level reasoning
* Tools = ground truth execution

and is the same pattern used in:

* LangChain
* AutoGPT
* Devin
* OpenAI Swarm
* ReAct-style systems
* Every production “LLM agent”

# **What Iteration 5 Introduces**

### ✔ 1. **Trusted Tool: `compute(op, a, b)`**

A Python function that performs the arithmetic using reliable code.

```python
def compute(op: str, a: int, b: int) -> int:
    if op == "ADD": return a + b
    if op == "SUB": return a - b
    if op == "MUL": return a * b
    raise ValueError("invalid op")
```

This is the first *tool*.

### ✔ 2. **Worker calls the tool, NOT the LLM**

The Worker agent becomes a **hybrid LLM + Python** actor:

* LLM reads the task
* LLM decides *to call the tool*
* Python executes the tool
* Worker returns correct JSON

All hallucination risk for calculation disappears.

### ✔ 3. **Critic becomes trivial**

Critic now checks a worker result that is almost always correct.
It still exists to maintain structure and catch formatting mistakes.

### ✔ 4. **Supervisor stays the same**

Supervisor logic does not change.
It automatically benefits from a trustworthy Worker.

### ✔ 5. **A new prompt protocol for tool use**

The Worker prompt changes from:

> “Compute the result yourself”

to:

> “Always call the provided tool to compute the result.
> Never compute inside the LLM.”

We add a line:

```
You MUST NOT perform arithmetic yourself. Always output {"tool_call": {"op":..., "a":..., "b":...}}
```

…and the Python Worker then executes that call.

# **Directory Structure (Recommended)**

```
Iteration_5/
    README.md         <-- this file
    compute.py        <-- trusted tool
    agents.py         <-- planner / worker / critic, new worker wrapper
    supervisor.py     <-- unchanged from Iteration 4
    schemas.py        <-- unchanged
    protocols.py
    logging_config.py
    main.py
```

# **Example Flow**

Planner → “ADD 12 and 7”

Worker LLM →
`{"tool_call": {"op": "ADD", "a": 12, "b": 7}}`

Worker Python →
calls `compute("ADD", 12, 7)` → returns `19`

Worker →
`{"result": 19}`

Critic →
`ACCEPT`

Supervisor →
run completed in 1 loop.

# **Benefits**

| Before (Iter 1–4)              | After (Iter 5)                  |
| ------------------------------ | ------------------------------- |
| Worker hallucinated arithmetic | Worker never hallucinates       |
| Critic often disagreed         | Critic becomes stable           |
| Unreliable feedback loops      | Reliable loops                  |
| Nondeterministic task success  | Deterministic, correct results  |
| LLM did everything             | LLM + tools (real architecture) |

# **Success Criteria for Iteration 5**

You are done when:

* Worker prompt explicitly instructs tool-use.
* Worker Python wrapper calls `compute()` deterministically.
* Worker always returns valid JSON with correct results.
* Critic never rejects correct outputs.
* Supervisor loops drop to nearly always **1**.

# **Next Step (Iteration 6)**

Introduce **multiple tools** and **tool-selection reasoning**.

Planner asks for a task → Worker chooses:

* computation tool
* lookup tool
* file read tool
* external API tool
* or none

This is where agents become *capable*.

