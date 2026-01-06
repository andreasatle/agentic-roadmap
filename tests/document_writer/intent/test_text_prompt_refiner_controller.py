from document_writer.domain.intent.text_prompt_refiner import TextPromptRefinerController, TextPromptRefinerInput
from agentic.protocols import AgentProtocol


class FakeAgent(AgentProtocol[TextPromptRefinerInput, str]):  # type: ignore[misc]
    name = "fake-refiner"
    input_schema = TextPromptRefinerInput
    output_schema = str  # type: ignore[assignment]
    id = "fake-id"
    model = "fake-model"

    def __call__(self, _: str) -> str:
        return "I want help summarizing my messy notes into a clear brief without changing meaning."


def test_text_prompt_refiner_semantic_preserving():
    controller = TextPromptRefinerController(agent=FakeAgent())
    messy_input = (
        "uh, so, like, I'm thinking maybe I need help summarizing my messy notes into a brief? "
        "not sure, but don't change what I meant."
    )
    output = controller(messy_input)

    assert isinstance(output, str)
    assert output.strip()
    assert "summarizing" in output.lower()
    assert "messy" in output.lower()
    assert "notes" in output.lower()

    # Ensure no structure is introduced
    assert "\n" not in output
    assert "#" not in output
    assert "-" not in output
    assert ":" not in output.split()[0]  # no metadata prefix

    # Ensure no new domain concepts appeared
    forbidden = ["plan", "structure", "section", "outline", "task", "document"]
    lowered = output.lower()
    assert all(term not in lowered for term in forbidden)
