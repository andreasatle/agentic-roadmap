# src/domain/writer/README.md

## Writer Domain

The Writer domain implements a **multi-section article generator** using the agentic framework.

### State Model

* **WriterDomainState**

  * Persistent, load/save capable
  * Owns high-level progression metadata

* **WriterContextState**

  * Holds generated section content
  * Tracks `sections` and `section_order`

### Planner Responsibilities

* Select next section
* Decide operation (`draft` vs `refine`)
* Optionally emit `section_order`

### Worker Responsibilities

* Produce JSON-only output
* Merge text only in `refine` mode
* Never invent structure

### Critic Responsibilities

* Single-section validation only
* Reject empty output
* Accept everything else (MVP)

The Writer is designed to become **topic-agnostic** once prompt cleanup is complete.
