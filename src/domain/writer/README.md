# src/domain/writer/README.md

## Writer Domain

- Writer executes exactly one atomic task per invocation.
- Tasks are explicit: `DraftSectionTask` or `RefineSectionTask` (discriminated by `kind`).
- Planner is a validator/router only: it checks structure membership and routes to the correct worker; it does not invent structure or modify tasks.
- Two independent workers:
  - `writer-draft-worker` writes new sections.
  - `writer-refine-worker` refines existing sections.
- No shared logic between workers; each has its own prompt and responsibility.
- Writer does not manage documents or persist structure; any orchestration happens outside this domain.
