````md
# DOMAIN_INTENT_API.md

## Status and semantic closure

This subtree **IS semantically closed** with respect to the Intent domain’s own contracts.

All referenced types and behaviors required to understand **Intent creation, representation, and loading** are defined within this snapshot. External dependencies (`agentic.*`, YAML parser, logging) are used only as execution mechanisms and do not affect the semantic contract of the Intent domain.

---

## 1. Purpose and authority boundaries

### Domain purpose
The Intent domain defines a **non-executable, advisory representation of user intent**. Its sole responsibility is to **capture, normalize, and transport intent signals** without performing planning, execution, traversal, or decision-making.

### Authority boundaries
The Intent domain:

- **MUST NOT** plan, execute, or control workflows.
- **MUST NOT** create document structure, tasks, or ordering.
- **MUST NOT** infer, resolve, or invent intent beyond what is explicitly provided.
- **MUST NOT** enforce intent on downstream domains.
- **MUST** remain passive, declarative, and advisory-only.

Downstream domains (e.g. Document, Writer) MAY consume intent, but **retain full authority** over whether and how it is applied.

---

## 2. Core public entities

### 2.1 `IntentEnvelope`

#### Type (normative)
```python
class IntentEnvelope(BaseModel):
    structural_intent: StructuralIntent
    semantic_constraints: GlobalSemanticConstraints
    stylistic_preferences: StylisticPreferences
````

#### Semantics

* The `IntentEnvelope` is a **pure data container**.
* It groups intent signals without interpretation.
* Presence of any field **does not imply obligation** for downstream consumers.

---

### 2.2 `StructuralIntent`

#### Type

```python
class StructuralIntent(BaseModel):
    document_goal: str | None
    audience: str | None
    tone: str | None
    required_sections: list[str]
    forbidden_sections: list[str]
```

#### Semantics (normative)

* Signals MAY influence structure, but:

  * **MUST NOT** create, delete, reorder, or rename structure by themselves.
  * **MUST NOT** imply hierarchy or section identity.
* `required_sections` and `forbidden_sections` are **labels only**, not commands.

---

### 2.3 `GlobalSemanticConstraints`

#### Type

```python
class GlobalSemanticConstraints(BaseModel):
    must_include: list[str]
    must_avoid: list[str]
    required_mentions: list[str]
```

#### Semantics

* Constraints are **placement-agnostic**.
* They do not bind to sections, nodes, or order.
* They are **global expectations**, not enforcement rules.

---

### 2.4 `StylisticPreferences`

#### Type

```python
class StylisticPreferences(BaseModel):
    humor_level: str | None
    formality: str | None
    narrative_voice: str | None
```

#### Semantics

* Soft preferences only.
* **Non-binding** and **non-authoritative**.
* Consumers MAY ignore these entirely.

---

## 3. Intent creation controllers

### 3.1 `TextIntentController`

#### Purpose

Projects raw user text into an `IntentEnvelope` in a **single, advisory pass**.

#### Type

```python
@dataclass
class TextIntentController:
    agent: AgentProtocol[TextIntentInput, IntentEnvelope]
```

#### Invocation

```python
IntentEnvelope = controller(text: str)
```

#### Semantics (normative)

* Extracts intent signals only.
* **MUST NOT**:

  * plan
  * execute
  * infer structure
  * invent hierarchy
  * emit tasks
* Output MUST conform strictly to `IntentEnvelope`.

---

### 3.2 `TextIntentInput`

```python
class TextIntentInput(BaseModel):
    text: str
```

* Sole input: raw user text.
* No metadata, no structure.

---

### 3.3 `make_text_intent_controller(...)`

```python
make_text_intent_controller(
    *,
    model: str = "gpt-4.1-mini",
) -> TextIntentController
```

#### Guarantees

* Uses a deterministic, schema-validated agent.
* Temperature = 0.0.
* Strict JSON output enforced.

---

## 4. Text prompt refinement (non-intent)

### 4.1 `TextPromptRefinerController`

#### Purpose

Clarifies raw user text **without extracting intent**.

#### Semantics (normative)

The refiner:

* **MUST preserve meaning exactly**
* **MUST expose ambiguity**, not resolve it
* **MUST NOT**:

  * extract intent
  * plan
  * create structure
  * generate documents
  * introduce new ideas

#### Invocation

```python
refined_text: str = controller(text: str)
```

---

### 4.2 `TextPromptRefinerInput`

```python
class TextPromptRefinerInput(BaseModel):
    text: str
```

---

### 4.3 `make_text_prompt_refiner_controller(...)`

Creates a refiner that:

* Returns plain prose only
* No metadata
* No JSON
* No commentary

---

## 5. YAML loading API

### 5.1 `load_intent_from_yaml(yaml_text: str) -> IntentEnvelope`

#### Semantics

* Parses YAML into `IntentEnvelope`.
* **MUST reject unknown top-level keys**.
* Performs **no inference**.

---

### 5.2 `load_intent_from_file(path: str | Path) -> IntentEnvelope`

* Loads YAML from file.
* Delegates validation to schema.

---

## 6. Invariants (global)

The Intent domain MUST:

* Remain **execution-free**
* Remain **domain-agnostic**
* Remain **side-effect free**
* Remain **schema-validated**
* Remain **non-authoritative**

Intent data MAY be ignored by any downstream consumer without violating contract.

---

## 7. Explicit non-features / forbidden behavior

The Intent domain MUST NOT:

* Create or modify document structure
* Emit tasks
* Bind intent to specific nodes
* Resolve conflicts between intent fields
* Enforce semantic or stylistic constraints
* Store state across calls
* Depend on project context or prior execution

---

## 8. Extension points

* New intent fields MAY be added only by extending schemas.
* Controllers MAY evolve prompt wording, provided:

  * Output schema remains identical
  * Advisory-only semantics are preserved
* Additional loaders (e.g. JSON) may be added if schema rules are enforced.

---

## 9. Canonical interpretation

The `IntentEnvelope` is **canonized** as:

> A passive, advisory signal bundle whose presence never implies authority.

Any system behavior that treats intent as binding, mandatory, or executable is **violating this API**.

**End of DOMAIN_INTENT_API.md**