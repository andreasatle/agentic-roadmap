#!/usr/bin/env python3
import pathlib

# The bootstrap prompt inserted verbatim at the top of the output file
BOOTSTRAP_PROMPT = """AGENTIC PROJECT BOOTSTRAP PROMPT (PASTE AT START OF NEW SESSION)

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
Supervisor must remain domain-independent.
No structural changes unless I explicitly request them.
All code must remain strict-schema validated.

Your role:
Keep critiques strong and eliminate fluff.
Ask clarifying questions when anything is ambiguous.
Prefer surgical patches over large rewrites.
Never assume brainstorming unless I explicitly say “brainstorm.”

END OF BOOTSTRAP PROMPT

---------------------------------------------------------------------

"""

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
