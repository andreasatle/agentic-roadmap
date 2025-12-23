# APP_WEB_API.md

**Normative API Specification — `src/apps/web`**

---

## 1. Scope and Authority

This document defines the **authoritative API contract** for the `src/apps/web` subtree.

* This API specification is **normative**.
* If implementation behavior deviates from this document, **the implementation is incorrect**.
* Only files explicitly included in the snapshot are considered authoritative.
* All referenced but missing modules are treated as **external dependencies with unknown semantics**.

This API layer provides a **stateless HTTP interface** for:

* Parsing and serializing *IntentEnvelope* objects
* Generating markdown documents from an intent
* Returning downloadable artifacts via HTTP streaming

---

## 2. External Dependencies (Explicitly Unknown Semantics)

The following symbols are referenced but **not defined** in this subtree:

| Dependency                                       | Usage               | Semantics                                              |
| ------------------------------------------------ | ------------------- | ------------------------------------------------------ |
| `domain.intent.load_intent_from_yaml`            | Intent parsing      | Unknown validation, normalization, and error semantics |
| `domain.intent.types.IntentEnvelope`             | Core intent schema  | Structure partially inferred via usage only            |
| `apps.document_writer.service.generate_document` | Document generation | Execution model, determinism, cost, retries unknown    |
| `result.markdown`                                | Generation output   | Assumed to be a string                                 |

No guarantees are made about:

* validation strictness
* determinism
* performance
* cost
* retries
* concurrency behavior

---

## 3. Application Characteristics

### 3.1 Execution Model

* **Stateless**: No server-side persistence.
* **Request-scoped execution** only.
* **No user identity**, authentication, or session tracking.
* **No background tasks** or asynchronous job management.
* **Synchronous request–response semantics**.

---

## 4. Public HTTP API

### 4.1 `GET /`

**Purpose**
Serve the HTML UI entrypoint.

**Response**

* Content-Type: `text/html`
* Body: Rendered `index.html` template

**Semantics**

* MUST NOT mutate state
* MUST NOT perform intent parsing or document generation

---

### 4.2 `POST /intent/parse`

**Purpose**
Parse raw YAML text into a validated `IntentEnvelope`.

#### Request Body — `IntentParseRequest`

```json
{
  "yaml_text": "string"
}
```

**Constraints**

* `yaml_text` MUST be a string
* Content MUST represent a valid IntentEnvelope according to external parser rules

#### Response (Success)

* Status: `200 OK`
* Body: JSON serialization of `IntentEnvelope` via `model_dump()`

```json
{ "...": "IntentEnvelope fields" }
```

#### Response (Failure)

* Status: `400 Bad Request`
* Body: `{ "detail": "<error message>" }`

**Failure Semantics**

* Any exception during parsing MUST be translated into HTTP 400
* No partial results are returned

---

### 4.3 `POST /intent/save`

**Purpose**
Serialize an `IntentEnvelope` to YAML and return it as a downloadable file.

#### Request Body — `IntentSaveRequest`

```json
{
  "intent": { "...": "IntentEnvelope" },
  "filename": "string | null"
}
```

#### Filename Resolution Rules (Normative)

1. If `filename` is `None` or empty after `.strip()`:

   * Use `"intent.yaml"`
2. Otherwise:

   * Use provided filename verbatim

#### Response

* Status: `200 OK`
* Content-Type: `text/yaml`
* Header:

  ```
  Content-Disposition: attachment; filename="<resolved filename>"
  ```
* Body: YAML serialization of `intent.model_dump()`

**Invariants**

* MUST NOT persist files server-side
* MUST stream content via HTTP response only

---

### 4.4 `POST /document/generate`

**Purpose**
Generate a markdown document from a provided `IntentEnvelope`.

#### Request Body — `DocumentGenerateRequest`

```json
{
  "intent": { "...": "IntentEnvelope" }
}
```

#### Execution Semantics

* The API extracts:

  * `intent.structural_intent.document_goal`
  * `intent.structural_intent.audience`
  * `intent.structural_intent.tone`
* These fields are forwarded to `generate_document(...)`
* `trace` is **always `False`**

#### Response (Success)

```json
{
  "markdown": "string"
}
```

**Invariants**

* Returned markdown MUST be a string
* No streaming or partial updates are supported
* Generation MUST complete before response returns

**Non-Features**

* No progress reporting
* No cancellation
* No retries at this layer

---

### 4.5 `POST /document/save`

**Purpose**
Return generated markdown as a downloadable file.

#### Request Body — `DocumentSaveRequest`

```json
{
  "markdown": "string",
  "filename": "string | null"
}
```

#### Filename Resolution Rules (Normative)

1. If `filename` is `None` or empty after `.strip()`:

   * Use `"article.md"`
2. Otherwise:

   * Use provided filename verbatim

#### Response

* Status: `200 OK`
* Content-Type: `text/markdown`
* Header:

  ```
  Content-Disposition: attachment; filename="<resolved filename>"
  ```
* Body: Raw markdown content

**Invariants**

* MUST NOT validate markdown content
* MUST NOT modify markdown content
* MUST NOT persist output server-side

---

## 5. Core Data Contracts

### 5.1 `IntentEnvelope` (External)

* Treated as an **opaque but structured object**
* MUST support `.model_dump()`
* MUST contain:

  * `structural_intent.document_goal`
  * `structural_intent.audience`
  * `structural_intent.tone`

No other fields are relied upon by this API layer.

---

## 6. Security and Isolation

**Explicitly Absent**

* Authentication
* Authorization
* Rate limiting
* Input size limits
* Sandbox execution

This API MUST be treated as **unsafe for public exposure** without an external security layer.

---

## 7. Extension Points

This API explicitly allows extension via:

* Replacing `generate_document(...)`
* Changing `IntentEnvelope` structure (if compatible)
* Adding new endpoints under `/document/*` or `/intent/*`

This API explicitly **does not** support:

* Stateful workflows
* Multi-user coordination
* Background jobs
* Partial or streaming generation

---

## 8. Failure Mode Assessment

### Is the subtree semantically closed?

**NO.**

The following are required for full semantic closure and are missing:

1. Definition of `IntentEnvelope`
2. Validation and normalization rules for intents
3. Semantics of `generate_document`
4. Error behavior and determinism guarantees
5. Performance and cost characteristics

These omissions are **explicit and intentional**.

---

## 9. Summary (Normative)

* This API is a **pure stateless orchestration layer**
* It owns **HTTP contracts only**
* It delegates all domain logic externally
* It guarantees **no persistence, no side effects, no hidden state**

This document is sufficient for:

* Correct client implementation
* Reasoning about behavior
* Re-implementation of the API layer

without access to the underlying code.
