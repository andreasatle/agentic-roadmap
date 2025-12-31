````md
# DOMAIN_DOCUMENT_API.md

## Status and semantic closure

This subtree is **NOT semantically closed**.

The snapshot references types not defined in this snapshot:

- `domain.document_writer.intent.types.IntentEnvelope` (required to type the `intent` field and to interpret “advisory intent” semantics).
- `agentic.agent_dispatcher.AgentDispatcher` (used as a required dependency in `api.analyze()` and constructed in `main.py`; its required interface is not defined here).
- `agentic.analysis_controller.AnalysisControllerRequest` and `run_analysis_controller` (the execution semantics of analysis are delegated to Agentic; not defined here).

The API below is therefore **normative only for the Document domain boundary** and its own types/contracts. Anything delegated to the missing dependencies is specified as an external requirement.

---

## 1. Purpose and authority boundaries

### Domain purpose
The Document domain defines and owns the **immutable document structure** used to guide writing. Its primary artifact is a `DocumentTree` composed of `DocumentNode`s.

### Authority boundaries
The Document domain:

- **MUST** own all structural authority (creation, deletion, ordering, and meaning of nodes).
- **MUST NOT** delegate structural authority to intent or to the Writer domain.
- **MUST** treat intent as **advisory input only** when no existing structure is provided.
- **MUST** preserve an existing `DocumentTree` when one is provided, and **MUST ignore intent** in that case.
- **MUST NOT** perform writing, critique, tool invocation, or multi-step execution within this domain.

The Writer domain (external) is assumed to consume `DocumentTree` as read-only context; the Document domain is the sole owner of structural truth.

---

## 2. Core public API surface

### 2.1 `domain.document_writer.document.api.analyze(...)`

#### Signature (normative)
```python
analyze(
    *,
    document_tree: DocumentTree | None,
    tone: str | None,
    audience: str | None,
    goal: str | None,
    intent: IntentEnvelope | None = None,
    dispatcher: AgentDispatcher,
) -> DocumentAnalysisResult
````

#### Behavior

* This is a **planner-only analysis call**.
* It **constructs a `DocumentPlannerInput`** from the provided arguments.
* It **delegates** execution to the external analysis controller (`run_analysis_controller`) with an `AnalysisControllerRequest(planner_input=...)`.
* It returns a `DocumentAnalysisResult` wrapper containing:

  * the delegated controller response (opaque to this domain)
  * a domain-owned `intent_observation` string.

#### Intent observation (normative)

`intent_observation` MUST be set as follows:

* If `document_tree is not None`: `"ignored_existing_structure"`
* Else if `document_tree is None` and `intent is not None`: `"intent_advisory_available"`
* Else: `"no_intent_provided"`

This observation is **diagnostic only** and MUST NOT alter execution.

#### External requirements

* `dispatcher` MUST be compatible with the analysis controller’s expectations (planner-only execution). Exact required interface is defined outside this snapshot.

---

### 2.2 `DocumentAnalysisResult`

#### Type

A dataclass wrapper:

* `controller_response: any` (opaque delegated response)
* `intent_observation: str`

#### Behavior

* Attribute access MUST delegate to `controller_response` via `__getattr__`.
* This wrapper is **observability-only**: it MUST NOT change the delegated behavior.

---

### 2.3 `domain.document_writer.document.content.ContentStore`

#### Type

```python
class ContentStore(BaseModel):
    by_node_id: dict[str, str] = {}
```

#### Semantics

* Maps `DocumentNode.id` → section text.
* Content is intentionally **separate from structure**; this domain does not bind, order, or assemble text.

---

## 3. Structural model contracts

### 3.1 `DocumentNode`

#### Type

```python
class DocumentNode(BaseModel):
    id: str
    title: str
    description: str
    children: list[DocumentNode] = []
```

#### Semantics (normative)

* `id` MUST be:

  * opaque (no required format)
  * unique within a `DocumentTree`
  * stable for the duration of any writer run that consumes the tree
* `title` is the human-readable section label.
* `description` is the **semantic obligation** for writing that node’s content.
* `children` define the outline hierarchy.

#### Mutability

Despite an “immutable” description in the docstring, the snapshot does not enforce immutability via model configuration. Normatively, consumers MUST treat `DocumentNode` as **read-only structure** for a run.

---

### 3.2 `DocumentTree`

#### Type

```python
class DocumentTree(BaseModel):
    root: DocumentNode
```

#### Semantics (normative)

* `root` MUST always be present.
* The tree MUST represent the complete outline for a run.
* The tree MUST NOT include content; content lives externally (e.g., `ContentStore`).

---

## 4. Planner I/O contracts

### 4.1 `DocumentPlannerInput`

#### Type

```python
class DocumentPlannerInput(BaseModel):
    document_tree: DocumentTree | None = None
    tone: str | None = None
    audience: str | None = None
    goal: str | None = None
    intent: IntentEnvelope | None = None
```

#### Semantics (normative)

* `intent` is advisory and read-only.
* If `document_tree` is provided, intent MUST be ignored by the planner.
* `tone`, `audience`, `goal` are optional context for initial planning when `document_tree is None`.

---

### 4.2 `DocumentPlannerOutput`

#### Type

```python
class DocumentPlannerOutput(BaseModel):
    document_tree: DocumentTree
    applies_thesis_rule: bool | None = None
```

#### Semantics (normative)

* MUST always output exactly one `document_tree`.
* `applies_thesis_rule` is optional and, when true, indicates the tree was generated under thesis constraints.

---

## 5. Planner execution semantics (normative, delegated)

### 5.1 Planner-only controller requirement

The Document domain is defined to be executed under a **planner-only controller** (external). Therefore:

* The execution MUST invoke the planner exactly once per analysis request.
* No workers, tools, or critics are part of the Document analysis run.

This is an external guarantee; the Document domain requires it.

---

## 6. Document planner semantics (prompt-defined, normative)

The Document planner’s normative behavior is defined by the contract in `planner.PROMPT_PLANNER`.

### 6.1 Output obligation

* MUST emit exactly one `DocumentTree` with a `root` node.
* MUST return strict JSON matching `DocumentPlannerOutput`.

### 6.2 Existing structure rule

If input `document_tree` is not null:

* Planner MUST preserve the provided structure.
* Planner MUST ignore `intent` entirely.

### 6.3 Initial structure rule

If input `document_tree` is null:

* Planner MUST construct a complete tree:

  * Root node describing overall document
  * Child nodes representing sections
  * Child nodes MUST have `children=[]` (flat section list) unless the planner’s “no hierarchy” rule is interpreted otherwise; normatively, the prompt states “do not add hierarchy”.

### 6.4 Intent advisory rule (only on init)

When `document_tree is null`, planner MAY consider intent as advisory, with strict limits:

* MAY use `structural_intent.required_sections` to inspire titles if coherent.
* MAY use `structural_intent.forbidden_sections` to guide naming avoidance but MUST NOT suppress needed sections.
* MUST NOT let:

  * `semantic_constraints`
  * `stylistic_preferences`
    affect structure.
* MUST ignore intent signals that conflict with coherence.
* Intent MUST NOT directly create/delete/reorder nodes; the planner owns all structural authority.

**Note:** `structural_intent`, `semantic_constraints`, `stylistic_preferences` are referenced but not typed in this snapshot (they are presumably inside `IntentEnvelope`). Their exact schema is unknown.

### 6.5 Thesis rule (conditional)

If the planner judges the document as a “linear reading doc” (blog post / reflective article / explanatory essay), it MUST apply thesis requirements:

* MUST produce exactly one thesis sentence, labeled `Thesis: ...` in the plan (specifically within descriptions).
* MUST include distinct `Introduction` and `Conclusion` nodes.
* MUST place the thesis in the Introduction node description.
* MUST ensure Conclusion revisits thesis without verbatim repetition.
* MUST set `applies_thesis_rule=true`.
* MUST NOT apply thesis requirements to reference docs, logs/reports, exploratory notes.
* MUST NOT emit multiple theses.

---

## 7. `DocumentTask` (present but unused by public API)

### 7.1 Type

```python
class DocumentTask(BaseModel):
    op: Literal["init", "split", "merge", "reorder", "delete", "emit_writer_tasks"]
    target: str | None = None
    parameters: dict[str, Any] = {}
```

### 7.2 Validation semantics (normative)

The `validate_semantics` validator MUST enforce:

* `init`:

  * `target` MUST be `None`
  * `parameters.root` MUST exist and MUST be a `DocumentNode`
* `split`:

  * `target` MUST be a non-empty node id
  * `parameters.children` MUST be `list[DocumentNode]`
* `merge`:

  * `parameters.source_ids` MUST be `list[str]` (non-empty)
  * `parameters.new_node` MUST be `DocumentNode`
* `reorder`:

  * `parameters.parent_id` MUST be `str`
  * `parameters.ordered_child_ids` MUST be `list[str]` (non-empty)
* `delete`:

  * `target` MUST be a non-empty node id
  * `parameters` MUST be empty
* `emit_writer_tasks`:

  * No additional validation in this snapshot.

### 7.3 Notes / gaps

* This snapshot does not define any executor that applies `DocumentTask` to a `DocumentTree`.
* Therefore, `DocumentTask` is currently a **validated command schema without execution semantics** in this subtree.

---

## 8. Extension points

* The planner may evolve its initial tree construction strategy, provided it continues to:

  * always output a complete `DocumentTree`
  * preserve provided `document_tree`
  * enforce the thesis rule when applicable
  * respect the advisory-only intent constraints

* `DocumentTask` suggests future support for structural transformations (`split/merge/reorder/delete`), but no executor is defined here.

---

## 9. Explicit non-features / forbidden behavior

The Document domain MUST NOT:

* execute writer tasks
* emit writer tasks as its output artifact (only structure)
* call workers, critics, or tools during `analyze`
* persist structure or content
* treat intent as authoritative
* modify an existing provided structure based on intent
* require intent fields to be present (intent is optional; schema unknown here)

---

## 10. Minimal usage contract (informative but normative at boundaries)

To perform a document analysis run:

* Caller provides:

  * `document_tree=None` for initial planning (or an existing `DocumentTree` to preserve)
  * optional `tone/audience/goal`
  * optional `intent` (advisory only; ignored if structure exists)
  * a planner-capable `dispatcher` compatible with planner-only execution

* Result provides:

  * `plan` (delegated controller response, expected to include a `DocumentTree`)
  * `intent_observation` describing whether intent was available or ignored

**End of DOMAIN_DOCUMENT_API.md**
