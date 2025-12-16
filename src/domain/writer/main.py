
import argparse
from dotenv import load_dotenv

from domain.writer import (
    make_agent_dispatcher,
    make_tool_registry,
)
from domain.writer.state import StructureState
from domain.writer.api import run
from domain.writer.schemas import WriterDomainState
from domain.writer.types import DraftSectionTask


def _pretty_print_run(run: dict) -> None:
    """Render the single-task writer execution result."""
    def _serialize(value):
        return value.model_dump() if hasattr(value, "model_dump") else value

    plan = run.task
    result = run.worker_output
    decision = run.critic_decision

    print("Writer supervisor run complete:")
    print(f"  Plan: {_serialize(plan)}")
    print(f"  Result: {_serialize(result)}")
    print(f"  Decision: {_serialize(decision)}")
    if run.trace:
        print("  Trace:")
        for entry in run.trace:
            print(f"    {_serialize(entry)}")


def main() -> None:
    load_dotenv(override=True)
    parser = argparse.ArgumentParser(description="Run the writer supervisor.")
    parser.add_argument("--instructions", type=str, default="", help="Opaque task instructions.")
    parser.add_argument("--sections", type=str, default="", help="Comma-separated list of section names.")
    args = parser.parse_args()

    instructions = args.instructions.strip()
    tool_registry = make_tool_registry()
    sections_arg = [s.strip() for s in args.sections.split(",") if s.strip()]
    if not sections_arg:
        raise RuntimeError(
            "Writer requires an explicit structure: no sections were provided."
        )
    state = WriterDomainState(structure=StructureState(sections=sections_arg))

    section_name = state.structure.sections[0]
    task = DraftSectionTask(
        section_name=section_name,
        purpose=f"Write the '{section_name}' section.",
        requirements=[instructions or "Write the section content clearly."],
    )
    dispatcher = make_agent_dispatcher(model="gpt-4.1-mini", max_retries=3)
    result = run(
        task,
        dispatcher=dispatcher,
        tool_registry=tool_registry,
        domain_state=state,
    )

    _pretty_print_run(result)


if __name__ == "__main__":
    main()
