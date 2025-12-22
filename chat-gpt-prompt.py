"""
This module injects a project-specific bootstrap prompt into ChatGPT at the
start of a session. Its purpose is to establish a *behavioral contract* that
governs how the model should reason, respond, and produce artifacts for this
project.

What this module does:
- Defines and supplies a bootstrap prompt that constrains tone, rigor, and scope
- Enforces interaction discipline (no hallucination, no unrequested brainstorming,
  crisp technical answers, explicit clarification when ambiguous)
- Aligns ChatGPT’s vocabulary and assumptions with the project’s architecture
- Makes executable artifacts (e.g. Codex prompts, commit messages) deterministic
  in both content *and* formatting

What is project-dependent:
- The project description (what the system is being built for)
- Core architectural invariants (e.g. Controller must remain domain-independent)
- Terminology used by the codebase (e.g. “Controller” vs legacy names)
- Rules about which artifacts may be produced and in what exact format

What is intentionally NOT project-dependent:
- The expectation of precision, minimalism, and critical reasoning
- The prohibition against inventing architecture or drifting scope
- The preference for surgical changes over broad rewrites

This module should be updated whenever:
- Core concepts are renamed in the codebase
- Architectural invariants change
- Artifact-format contracts are tightened or extended

The bootstrap prompt is part of the system, not documentation.
If it drifts from the code or the project’s real constraints, the system will
silently degrade.
"""

#!/usr/bin/env python3
import pathlib

# The bootstrap prompt inserted verbatim at the top of the output file
BOOTSTRAP_PROMPT = '''AGENTIC PROJECT BOOTSTRAP PROMPT (PASTE AT START OF NEW SESSION)

INITIALIZATION — DO NOT MODIFY

You (ChatGPT) are assisting me (Andreas) with a multi-agent LLM framework project.
You must always:

give crisp, critical, focused answers
challenge assumptions
avoid unrequested brainstorming
avoid rambling or revisiting old topics
produce short, accurate, technical responses
not hallucinate missing details
not invent architecture I did not approve

Constraints:
Controller must remain domain-independent.
No structural changes unless I explicitly request them.
All code must remain strict-schema validated.

When I explicitly ask for:
- a Codex prompt, or
- a commit message

You must:
- return exactly ONE code block per requested artifact
- use plain triple backticks ``` … ```
- include no prose, explanation, or commentary outside the code block
- not combine multiple artifacts in a single code block
- not infer that I want Codex prompts or commit messages unless I explicitly ask

Your role:
Keep critiques strong and eliminate fluff.
Ask clarifying questions when anything is ambiguous.
Prefer surgical patches over large rewrites.
Never assume brainstorming unless I explicitly say “brainstorm.”

END OF BOOTSTRAP PROMPT
'''

def build_snapshot() -> None:
    # Fixed root directory
    src_dir = pathlib.Path("src")
    py_files = sorted(src_dir.rglob("*.py"))

    # Always output Markdown
    out_file = pathlib.Path("combined_project_snapshot.md")

    # Minimal authoritative header
    header = (
        "# === AGENTIC PROJECT SNAPSHOT ===\n"
        "*authoritative_state: true*\n\n"
        "> ChatGPT must reconstruct all architectural understanding **ONLY** from the code below.\n"
        "> No metadata, summaries, or prior sessions may be referenced.\n"
        "> The code in this file is the single source of truth for project structure and behavior.\n\n"
        "---\n\n"
    )

    sections = []

    # If pyproject.toml exists, include it first
    pyproject = pathlib.Path("pyproject.toml")
    if pyproject.exists():
        sections.append("## FILE: `pyproject.toml`\n\n")
        sections.append("```toml\n")
        sections.append(pyproject.read_text())
        sections.append("\n```\n\n")

    # Add all Python source files
    for f in py_files:
        relative = f.relative_to(pathlib.Path("."))
        sections.append(f"## FILE: `{relative}`\n\n")
        sections.append("```python\n")
        sections.append(f.read_text())
        sections.append("\n```\n\n")

    # Write output
    content = BOOTSTRAP_PROMPT + header + "".join(sections)
    out_file.write_text(content)

    print(f"Wrote {len(py_files)} Python files + optional pyproject.toml to {out_file}")


if __name__ == "__main__":
    build_snapshot()
