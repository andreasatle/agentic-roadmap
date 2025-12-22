import json
from typing import Any

import gradio as gr
from pydantic import ValidationError

from domain.intent.types import IntentEnvelope


def _to_none(value: str) -> str | None:
    value = value.strip()
    return value if value else None


def _list_from_text(value: str) -> list[str]:
    separators = [",", "\n"]
    items: list[str] = [value]
    for sep in separators:
        next_items: list[str] = []
        for item in items:
            next_items.extend(item.split(sep))
        items = next_items
    return [item.strip() for item in items if item.strip()]


def build_intent(
    document_goal: str,
    audience_choice: str,
    audience_custom: str,
    tone: str,
    required_sections: str,
    forbidden_sections: str,
    must_include: str,
    must_avoid: str,
    required_mentions: str,
    humor_level: str,
    humor_level_custom: str,
    formality: str,
    formality_custom: str,
    narrative_voice: str,
    narrative_voice_custom: str,
) -> tuple[str, str]:
    audience_value = _to_none(audience_custom) if audience_choice == "Custom" else _to_none(audience_choice)
    data: dict[str, Any] = {
        "structural_intent": {
            "document_goal": _to_none(document_goal),
            "audience": audience_value,
            "tone": _to_none(tone),
            "required_sections": _list_from_text(required_sections),
            "forbidden_sections": _list_from_text(forbidden_sections),
        },
        "semantic_constraints": {
            "must_include": _list_from_text(must_include),
            "must_avoid": _list_from_text(must_avoid),
            "required_mentions": _list_from_text(required_mentions),
        },
        "stylistic_preferences": {
            "humor_level": _to_none(humor_level_custom) if humor_level == "Custom" else _to_none(humor_level),
            "formality": _to_none(formality_custom) if formality == "Custom" else _to_none(formality),
            "narrative_voice": _to_none(narrative_voice_custom)
            if narrative_voice == "Custom"
            else _to_none(narrative_voice),
        },
    }

    try:
        intent = IntentEnvelope.model_validate(data)
    except ValidationError as exc:
        return "", f"Validation error:\n{exc}"

    pretty_json = json.dumps(intent.model_dump(), indent=2)
    return pretty_json, ""


def main() -> None:
    with gr.Blocks(title="IntentEnvelope Preview") as demo:
        gr.Markdown("# IntentEnvelope Preview\nPure input surface; no execution.")

        with gr.Group():
            gr.Markdown("## Structural Intent")
            document_goal = gr.Textbox(label="Document Goal", lines=3, placeholder="Overall goal (optional)")
            audience_choice = gr.Dropdown(
                label="Audience",
                choices=["", "general", "executives", "engineers", "researchers", "Custom"],
                value="",
            )
            audience_custom = gr.Textbox(label="Audience (Custom)", placeholder="Used when Audience=Custom")
            tone = gr.Dropdown(
                label="Tone",
                choices=["", "informative", "reflective", "technical", "narrative", "other"],
                value="",
            )
            required_sections = gr.Textbox(
                label="Required Sections",
                placeholder="Comma or newline separated (optional)",
                lines=3,
            )
            forbidden_sections = gr.Textbox(
                label="Forbidden Sections",
                placeholder="Comma or newline separated (optional)",
                lines=3,
            )

        with gr.Group():
            gr.Markdown("## Semantic Constraints")
            must_include = gr.Textbox(
                label="Must Include",
                placeholder="Comma or newline separated (optional)",
                lines=2,
            )
            must_avoid = gr.Textbox(
                label="Must Avoid",
                placeholder="Comma or newline separated (optional)",
                lines=2,
            )
            required_mentions = gr.Textbox(
                label="Required Mentions",
                placeholder="Comma or newline separated (optional)",
                lines=2,
            )

        with gr.Group():
            gr.Markdown("## Stylistic Preferences")
            humor_level = gr.Dropdown(
                label="Humor Level",
                choices=["", "none", "light", "moderate", "Custom"],
                value="",
            )
            humor_level_custom = gr.Textbox(label="Humor Level (Custom)", placeholder="Used when Humor=Custom")
            formality = gr.Dropdown(
                label="Formality",
                choices=["", "informal", "neutral", "formal", "Custom"],
                value="",
            )
            formality_custom = gr.Textbox(label="Formality (Custom)", placeholder="Used when Formality=Custom")
            narrative_voice = gr.Dropdown(
                label="Narrative Voice",
                choices=["", "first-person", "third-person", "neutral", "Custom"],
                value="",
            )
            narrative_voice_custom = gr.Textbox(
                label="Narrative Voice (Custom)", placeholder="Used when Narrative Voice=Custom"
            )

        build_button = gr.Button("Build IntentEnvelope")
        json_output = gr.Code(label="IntentEnvelope (JSON)", language="json")
        error_output = gr.Textbox(label="Validation Errors", lines=6)

        inputs = [
            document_goal,
            audience_choice,
            audience_custom,
            tone,
            required_sections,
            forbidden_sections,
            must_include,
            must_avoid,
            required_mentions,
            humor_level,
            humor_level_custom,
            formality,
            formality_custom,
            narrative_voice,
            narrative_voice_custom,
        ]

        build_button.click(build_intent, inputs=inputs, outputs=[json_output, error_output])
        for control in inputs:
            control.change(build_intent, inputs=inputs, outputs=[json_output, error_output])

    demo.launch()


if __name__ == "__main__":
    main()
