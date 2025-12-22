```md
# APP_DOCUMENT_FROM_TEXT_EXECUTION.md

## Status and semantic closure

This subtree is **NOT semantically closed**.

The snapshot depends on the following external APIs whose contracts are not defined here:

- `domain.intent.*`  
  (`make_text_intent_controller`, `IntentEnvelope`, text refiner semantics)
- `domain.document.*`  
  (`make_planner`, `analyze`, `DocumentPlannerOutput`, `DocumentTree`, `DocumentNode`)
- `domain.writer.*`  
  (`execute_document`, writer dispatcher semantics, intent audit behavior)
- `agentic.agent_dispatcher.AgentDispatcher`  
  (planner-only vs full dispatcher execution semantics)

Accordingly, this document specifies **only the orchestration contract of the app layer** and explicitly treats all delegated behavior as opaque.

---

## 1. Purpose and authority boundaries

### App purpose

`document_from_text` is an **end-to-end orchestration app** that transforms raw user text into a fully written document by coordinating multiple domains in a fixed pipeline:

```

raw text
→ text refinement
→ intent extraction (advisory)
→ document structure planning
→ writer execution
→ markdown assembly

````

### Authority boundaries

This app:

- **OWNS orchestration order only**
- **DOES NOT own**:
  - intent semantics
  - document structure authority
  - writing correctness
  - critique or retry logic
- **MUST NOT** alter domain behavior
- **MUST treat all intent as advisory**

All planning, writing, and validation authority is delegated to domains.

---

## 2. CLI contract

### Invocation

The app is executed as a CLI module.

### Required input (mutually exclusive)

Exactly one of:

- `--text <string>`  
- `--text-path <path>`

### Optional flags

- `--out <path>`  
  Write assembled Markdown output to file instead of stdout.
- `--trace`  
  Print advisory intent observation and writer intent audit.
- `--print-intent`  
  Print parsed `IntentEnvelope` as YAML (read-only inspection).

### Invariants

- Providing both `--text` and `--text-path` MUST raise an error.
- Providing neither MUST raise an error.
- CLI performs no implicit defaults for document tone, audience, or goal.

---

## 3. Execution pipeline (normative ordering)

The app MUST execute the following steps **in order**:

### Step 1 — Read raw text

```python
raw_text = _read_text(args.text, args.text_path)
````

* Reads inline text or file contents.
* No preprocessing beyond I/O.

---

### Step 2 — Text prompt refinement

```python
refined_text = refiner(raw_text)
```

* Semantic-preserving clarification only.
* Output is plain text.
* No intent extraction here.

---

### Step 3 — Intent extraction (advisory)

```python
intent = intent_controller(refined_text)
```

* Produces an `IntentEnvelope`.
* Intent is advisory and non-authoritative.
* If `--print-intent` is set, the envelope is rendered as YAML.

---

### Step 4 — Document analysis (planner-only)

```python
analysis = analyze(
    document_tree=None,
    tone=None,
    audience=None,
    goal=None,
    intent=intent,
    dispatcher=planner_only_dispatcher,
)
```

Normative constraints:

* `document_tree` MUST be `None` (this app always plans from scratch).
* Dispatcher MUST be planner-only:

  * `workers = {}`
  * `critic = None`
* Intent MAY influence structure **only indirectly**, per Document domain rules.

The app MUST extract:

```python
planner_output = DocumentPlannerOutput.model_validate(analysis.plan)
planned_tree = planner_output.document_tree
```

---

### Step 5 — Writer execution

```python
writer_result = execute_document(
    document_tree=planned_tree,
    content_store=content_store,
    dispatcher=writer_dispatcher,
    tool_registry=writer_tool_registry,
    intent=intent,
    applies_thesis_rule=bool(planner_output.applies_thesis_rule),
)
```

Normative constraints:

* Writer receives:

  * the planned document tree
  * an empty `ContentStore`
  * the advisory intent
  * the thesis-rule flag determined by the document planner
* Writer controls retries, critique, and acceptance.
* This app does not intervene in writer decisions.

---

### Step 6 — Markdown assembly

```python
markdown_lines = assemble_markdown(planned_tree.root, writer_result.content_store)
```

#### Assembly rules (normative)

For each `DocumentNode`:

* Emit a Markdown heading based on depth:

  * `#` for root
  * `##`, `###`, … for descendants
* If content exists:

  * Strip a leading `<section_title>:` line if present
  * Preserve remaining prose verbatim
* Recurse depth-first over children

Assembly is **purely presentational**.

---

### Step 7 — Output

* If `--out` is provided, write to file.
* Otherwise, print to stdout.
* No additional formatting or post-processing is applied.

---

## 4. Public helper functions

### `_read_text(text, path) -> str`

* Enforces mutual exclusivity of inputs.
* Performs file read if `path` is provided.

### `assemble_markdown(node, store, depth=0) -> list[str]`

* Deterministic tree traversal.
* No semantic interpretation.
* No mutation of inputs.

---

## 5. Retry, atomicity, termination

* This app itself performs **no retries**.
* Retry behavior is entirely delegated to:

  * Document planner (single-shot)
  * Writer domain (bounded retries)
* Execution is linear and terminates after one full pipeline pass.

---

## 6. Explicit non-features / forbidden behavior

This app MUST NOT:

* Modify intent
* Modify document structure
* Generate writer tasks manually
* Enforce intent constraints
* Interpret semantic correctness
* Persist intermediate artifacts
* Skip pipeline stages
* Perform partial execution

---

## 7. Extension points

Permitted extensions:

* Alternative renderers (e.g. HTML instead of Markdown)
* Alternative input sources (e.g. stdin, API)
* Optional injection of tone/audience/goal into document analysis

Forbidden extensions:

* Introducing structural authority
* Making intent binding
* Collapsing domain boundaries
* Adding planner or writer logic here

---

## 8. Canonical interpretation

This app is canonized as:

> A **thin orchestration shell** that wires domains together without owning meaning, structure, or correctness.

Any behavior that treats this app as a decision-maker or authority is a violation of this API.

End of document.

