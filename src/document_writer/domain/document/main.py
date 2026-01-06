from dotenv import load_dotenv
from document_writer.domain.document.planner import make_planner
from document_writer.domain.document.api import analyze
from document_writer.domain.intent.types import IntentEnvelope
from agentic.agent_dispatcher import AgentDispatcher
from agentic.logging_config import get_logger

logger = get_logger("document_writer.domain.document.main")


def _pretty_print_run(run: dict, trace: bool = False) -> None:
    """Render the analysis supervisor output in a readable diagnostic summary."""
    def _serialize(value):
        return value.model_dump() if hasattr(value, "model_dump") else value

    print("Document analysis supervisor run complete:")
    print(f"  PlannerInput: {_serialize(run.planner_input)}")
    print(f"  Plan: {_serialize(run.plan)}")
    if trace and run.trace:
        print("  Trace:")
        for entry in run.trace:
            print(f"    {_serialize(entry)}")


def main() -> None:
    load_dotenv(override=True)

    # --- Planner-only dispatcher ---
    planner = make_planner(model="gpt-4.1-mini")
    dispatcher = AgentDispatcher(
        planner=planner,
        workers={},      # REQUIRED: empty, analysis-only
        critic=None,     # type: ignore[arg-type]
    )

    intent = IntentEnvelope()

    run = analyze(
        intent=intent,
        dispatcher=dispatcher,
    )

    _pretty_print_run(run)


if __name__ == "__main__":
    main()
