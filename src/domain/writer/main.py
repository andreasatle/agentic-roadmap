from __future__ import annotations

import argparse
from dotenv import load_dotenv
from openai import OpenAI

from domain.writer import (
    WriterPlannerInput,
    make_agent_dispatcher,
    make_tool_registry,
    problem_state_cls,
)
from agentic.supervisor import (
    SupervisorControlInput,
    SupervisorDomainInput,
    SupervisorRequest,
    run_supervisor,
)
from domain.writer.schemas import WriterDomainState
from domain.writer.types import WriterTask


def _pretty_print_run(run: dict) -> None:
    """Render the supervisor output in a readable diagnostic summary."""
    def _serialize(value):
        return value.model_dump() if hasattr(value, "model_dump") else value

    plan = run.plan
    result = run.result
    decision = run.decision
    loops_used = run.loops_used

    print("Writer supervisor run complete:")
    print(f"  Plan: {_serialize(plan)}")
    print(f"  Result: {_serialize(result)}")
    print(f"  Decision: {_serialize(decision)}")
    print(f"  Loops used: {loops_used}")


def main() -> None:
    load_dotenv(override=True)
    client = OpenAI()
    parser = argparse.ArgumentParser(description="Run the writer supervisor.")
    parser.add_argument("--instructions", type=str, default="", help="Opaque task instructions.")
    parser.add_argument("--max-iterations", type=int, default=1, help="Maximum supervisor iterations (capped at 10).")
    parser.add_argument("--fresh", action="store_true", help="Start with a fresh state (ignore persisted topic state).")
    args = parser.parse_args()

    instructions = args.instructions.strip()
    max_iterations = max(1, min(args.max_iterations, 10))
    tool_registry = make_tool_registry()
    state = WriterDomainState.load(topic=instructions or None) if not args.fresh else WriterDomainState(topic=instructions or None)
    structure_sections = state.structure.sections if state.structure else []
    if not structure_sections:
        state = state.model_copy(
            update={
                "structure": state.structure.model_copy(
                    update={
                        "sections": ["Introduction"],
                    }
                )
            }
        )
        structure_sections = state.structure.sections if state.structure else []
    if not structure_sections:
        raise RuntimeError(
            "Writer requires an explicit structure: no sections were provided in domain_state.structure.sections."
        )

    iteration = 0
    remaining = state.remaining_sections()
    while remaining and iteration < max_iterations:
        print(f"[writer] iteration {iteration + 1} / {max_iterations}")
        current_section = remaining[0]
        current_task = WriterTask(
            section_name=current_section,
            purpose=f"Write the '{current_section}' section.",
            operation="draft",
            requirements=[],
        )
        planner_input = WriterPlannerInput(
            task=current_task,
            instructions=instructions or None,
        )
        dispatcher = make_agent_dispatcher(client, model="gpt-4.1-mini", max_retries=3)
        supervisor_input = SupervisorRequest(
            control=SupervisorControlInput(max_loops=5),
            domain=SupervisorDomainInput(
                domain_state=state,
                planner_defaults=planner_input.model_dump(),
            ),
        )
        run = run_supervisor(
            supervisor_input,
            dispatcher=dispatcher,
            tool_registry=tool_registry,
            problem_state_cls=problem_state_cls,
        )
        state_data = run.project_state.get("domain_state") if run.project_state else None

        if state_data is not None:
            updated_state = WriterDomainState(**state_data)
            updated_state.save(topic=instructions or None)
            state = updated_state

        _pretty_print_run(run)
        iteration += 1
        remaining = state.remaining_sections()

    if iteration >= max_iterations and remaining:
        print("[writer] stopped after max_iterations without completion")
    if not remaining:
        print("[writer] structure exhausted")

    sections = state.content.sections
    order = state.content.section_order or sections.keys()
    article = "\n\n".join(sections[name] for name in order if name in sections)

    print(article)


if __name__ == "__main__":
    main()
