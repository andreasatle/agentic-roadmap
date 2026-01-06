from document_writer.domain.intent.controller import TextIntentController
from document_writer.domain.intent.types import IntentEnvelope, StructuralIntent, GlobalSemanticConstraints, StylisticPreferences


class FakeAgent:
    def __init__(self, output: dict):
        self.output = output
        self.name = "fake"
        self.input_schema = None
        self.output_schema = None
        self.id = "fake-id"
        self.model = "fake-model"

    def __call__(self, _: str) -> str:
        return IntentEnvelope(**self.output).model_dump_json()


def test_text_intent_controller_returns_intent_envelope():
    fake_output = {
        "structural_intent": {"document_goal": "Explain system", "audience": "Engineers", "tone": "concise"},
        "semantic_constraints": {"must_include": ["architecture"], "must_avoid": [], "required_mentions": []},
        "stylistic_preferences": {"humor_level": None, "formality": "medium", "narrative_voice": None},
    }
    controller = TextIntentController(agent=FakeAgent(fake_output))
    intent = controller("Describe the system.")
    assert isinstance(intent, IntentEnvelope)
    assert intent.structural_intent.document_goal == "Explain system"
    assert "architecture" in intent.semantic_constraints.must_include
    # Ensure no structural artifacts are injected
    assert intent.structural_intent.required_sections == []
    assert intent.structural_intent.forbidden_sections == []
