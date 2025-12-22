import json
from pathlib import Path
from typing import Any

import gradio as gr
import yaml
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
    narrative_voice: str,
    formality: str,
    humor_level: str,
) -> tuple[str, str, str]:
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
            "required_mentions": [],
        },
        "stylistic_preferences": {
            "narrative_voice": _to_none(narrative_voice),
            "formality": _to_none(formality),
            "humor_level": _to_none(humor_level),
        },
    }

    try:
        intent = IntentEnvelope.model_validate(data)
    except ValidationError as exc:
        return "", "", f"Validation error:\n{exc}"

    dumped = intent.model_dump()
    pretty_yaml = yaml.safe_dump(dumped, sort_keys=False, default_flow_style=False)
    pretty_json = json.dumps(dumped, indent=2)
    return pretty_json, pretty_yaml, ""


def save_yaml(yaml_text: str) -> str:
    path = Path("intent.yaml")
    path.write_text(yaml_text)
    return f"Saved to {path.resolve()}"


def main() -> None:
    with gr.Blocks(title="IntentEnvelope Builder") as demo:
        gr.Markdown("# IntentEnvelope Builder\nPure data capture for `IntentEnvelope` (no inference).")

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
                placeholder="Newline-separated list (optional)",
                lines=3,
            )
            forbidden_sections = gr.Textbox(
                label="Forbidden Sections",
                placeholder="Newline-separated list (optional)",
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

        with gr.Group():
            gr.Markdown("## Stylistic Preferences")
            narrative_voice = gr.Dropdown(
                label="Narrative Voice",
                choices=["", "first-person", "third-person", "neutral"],
                value="",
            )
            formality = gr.Dropdown(
                label="Formality",
                choices=["", "informal", "neutral", "formal"],
                value="",
            )
            humor_level = gr.Dropdown(
                label="Humor Level",
                choices=["", "none", "light", "moderate"],
                value="",
            )

        build_button = gr.Button("Build IntentEnvelope")
        save_button = gr.Button("Save YAML")
        json_output = gr.Code(label="IntentEnvelope (JSON)", language="json")
        yaml_output = gr.Code(label="IntentEnvelope (YAML)", language="yaml")
        error_output = gr.Textbox(label="Validation Errors", lines=6)
        save_status = gr.Textbox(label="Save Status", interactive=False)

        build_button.click(
            build_intent,
            inputs=[
                document_goal,
                audience_choice,
                audience_custom,
                tone,
                required_sections,
                forbidden_sections,
                must_include,
                must_avoid,
                narrative_voice,
                formality,
                humor_level,
            ],
            outputs=[json_output, yaml_output, error_output],
        )

        save_button.click(save_yaml, inputs=yaml_output, outputs=save_status)

    demo.launch()


if __name__ == "__main__":
    main()
