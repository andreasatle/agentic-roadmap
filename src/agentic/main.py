"""
The unified entrypoint has been split into domain-specific modules:
  - agentic.entrypoints.arithmetic_main
  - agentic.entrypoints.sentiment_main
  - agentic.entrypoints.coder_main
"""

from __future__ import annotations


def main() -> None:
    print(
        "Select a domain-specific entrypoint:\n"
        "  python -m agentic.entrypoints.arithmetic_main\n"
        "  python -m agentic.entrypoints.sentiment_main\n"
        "  python -m agentic.entrypoints.coder_main\n"
    )


if __name__ == "__main__":
    main()
