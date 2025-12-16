# src/domain/writer/README.md

## Writer Domain

- Writer is a single-task executor.
- It writes exactly one section per invocation.
- It is not a document manager and does not infer or persist structure.
- Planner validates provided structure and emits one `WriterTask`.
- Worker produces text for that task only; no merging or refinement of prior content.
- Any multi-section orchestration or persistence happens outside the writer domain.
