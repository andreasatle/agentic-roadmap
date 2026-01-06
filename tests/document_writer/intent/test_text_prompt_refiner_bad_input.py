from document_writer.domain.intent.text_prompt_refiner import (
    TextPromptRefinerController,
    TextPromptRefinerInput,
)
from agentic.protocols import AgentProtocol


class BadInputFakeAgent(AgentProtocol[TextPromptRefinerInput, str]):  # type: ignore[misc]
    name = "fake-refiner-bad"
    input_schema = TextPromptRefinerInput
    output_schema = str  # type: ignore[assignment]
    id = "fake-id"
    model = "fake-model"

    def __call__(self, _: str) -> str:
        # Shorter, denser, preserves core themes (overwhelm, deadlines)
        return "I'm overwhelmed by this project and looming deadlines; I need clarity on scope."


def test_text_prompt_refiner_normalizes_bad_input():
    controller = TextPromptRefinerController(agent=BadInputFakeAgent())
    raw = (
        "sooooo I'm like totally stressed out, this project is huge and messy, "
        "i dont even know what the scope is and deadlines are freaking me out, "
        "maybe I should just give up? idk, sorry for rambling"
    )
    refined = controller(raw)

    assert isinstance(refined, str)
    assert refined.strip()
    assert len(refined) < len(raw)

    # Core themes preserved
    lower_refined = refined.lower()
    for theme in ["project", "deadlines", "scope", "overwhelmed", "clarity"]:
        assert theme in lower_refined

    # No structure or headings introduced
    assert "\n" not in refined
    assert "#" not in refined
    assert "-" not in refined

    # Detect reduced filler/rambling
    assert lower_refined.count("um") + lower_refined.count("uh") == 0
    assert "sorry for rambling" not in lower_refined

    # No new goals or concepts introduced
    forbidden = ["section", "outline", "plan", "task", "article"]
    assert all(term not in lower_refined for term in forbidden)
