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
from agentic.supervisor import Supervisor
from domain.writer.schemas import WriterDomainState


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
    parser.add_argument("--topic", type=str, default="", help="Optional writing topic.")
    parser.add_argument("--tone", type=str, default="", help="Optional writing tone.")
    parser.add_argument("--audience", type=str, default="", help="Optional target audience.")
    parser.add_argument("--length", type=str, default="", help="Optional length guidance.")
    parser.add_argument("--max-iterations", type=int, default=1, help="Maximum supervisor iterations (capped at 10).")
    parser.add_argument("--fresh", action="store_true", help="Start with a fresh state (ignore persisted topic state).")
    args = parser.parse_args()

    topic = args.topic.strip()
    tone = args.tone.strip()
    audience = args.audience.strip()
    length = args.length.strip()
    max_iterations = max(1, min(args.max_iterations, 10))
    initial_planner_input = WriterPlannerInput(
        topic=topic or None,
        tone=tone or None,
        audience=audience or None,
        length=length or None,
    )

    tool_registry = make_tool_registry()
    state = WriterDomainState.load(topic=topic or None) if not args.fresh else WriterDomainState(topic=topic or None)

    for i in range(max_iterations):
        print(f"[writer] iteration {i + 1} / {max_iterations}")
        dispatcher = make_agent_dispatcher(client, model="gpt-4.1-mini", max_retries=3)
        supervisor = Supervisor(
            dispatcher=dispatcher,
            tool_registry=tool_registry,
            domain_state=state,
            max_loops=5,
            planner_defaults=initial_planner_input.model_dump(),
            problem_state_cls=problem_state_cls,
        )
        run = supervisor()
        updated_state = run.project_state.domain_state if run.project_state else None

        section_order = None
        for entry in run.trace or []:
            entry_state = entry.get("state") if isinstance(entry, dict) else None
            if getattr(entry_state, "name", None) != "PLAN":
                continue
            output = entry.get("output") if isinstance(entry, dict) else None
            if output is None:
                continue
            section_order = getattr(output, "section_order", None)
            if section_order:
                break

        if (
            updated_state is not None
            and updated_state.content is not None
            and not updated_state.content.section_order
            and section_order
            and run.plan is not None
            and run.result is not None
        ):
            updated_state = updated_state.update(
                task=run.plan,
                result=run.result,
                section_order=section_order,
            )

        if updated_state is not None:
            updated_state.save(topic=topic or None)
            state = updated_state

        _pretty_print_run(run)

    if max_iterations > 1:
        print("[writer] stopped after max_iterations without completion")

    sections = state.content.sections
    order = state.content.section_order or sections.keys()
    article = "\n\n".join(sections[name] for name in order if name in sections)

    print(article)


if __name__ == "__main__":
    main()
