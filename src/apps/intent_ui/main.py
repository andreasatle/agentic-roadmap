import json
from typing import Any

import gradio as gr
import yaml
from pydantic import ValidationError

from domain.intent.types import IntentEnvelope


def _to_none_if_empty(value: str) -> str | None:
    value = value.strip()
    return value if value else None


def _tags_from_text(value: str) -> list[str]:
    parts = [part.strip() for part in value.split(",") if part.strip()]
    return parts


def build_intent(
    document_goal: str,
    audience: str,
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
    data: dict[str, Any] = {
        "structural_intent": {
            "document_goal": _to_none_if_empty(document_goal),
            "audience": _to_none_if_empty(audience),
            "tone": _to_none_if_empty(tone),
            "required_sections": _tags_from_text(required_sections),
            "forbidden_sections": _tags_from_text(forbidden_sections),
        },
        "semantic_constraints": {
            "must_include": _tags_from_text(must_include),
            "must_avoid": _tags_from_text(must_avoid),
            "required_mentions": _tags_from_text(required_mentions),
        },
        "stylistic_preferences": {
            "humor_level": _to_none_if_empty(humor_level_custom)
            if humor_level == "Custom"
            else _to_none_if_empty(humor_level),
            "formality": _to_none_if_empty(formality_custom)
            if formality == "Custom"
            else _to_none_if_empty(formality),
            "narrative_voice": _to_none_if_empty(narrative_voice_custom)
            if narrative_voice == "Custom"
            else _to_none_if_empty(narrative_voice),
        },
    }

    try:
        intent = IntentEnvelope.model_validate(data)
    except ValidationError as exc:
        return "", f"Validation error:\n{exc}"

    pretty_json = json.dumps(intent.model_dump(), indent=2)
    pretty_yaml = yaml.safe_dump(intent.model_dump(), sort_keys=False, default_flow_style=False)
    return pretty_json, pretty_yaml


def main() -> None:
    with gr.Blocks(title="IntentEnvelope Builder") as demo:
        gr.Markdown("# IntentEnvelope Builder\nUse this form to capture intent explicitly (no inference).")

        with gr.Group():
            gr.Markdown("## Structural Intent")
            document_goal = gr.Textbox(label="Document Goal", lines=3, placeholder="Overall goal (optional)")
            audience = gr.Textbox(label="Audience", placeholder="Target audience (optional)")
            tone = gr.Textbox(label="Tone", placeholder="Desired tone (optional)")
            required_sections = gr.Textbox(
                label="Required Sections",
                placeholder="Comma-separated list (optional)",
            )
            forbidden_sections = gr.Textbox(
                label="Forbidden Sections",
                placeholder="Comma-separated list (optional)",
            )

        with gr.Group():
            gr.Markdown("## Semantic Constraints")
            must_include = gr.Textbox(
                label="Must Include",
                placeholder="Comma-separated list (optional)",
            )
            must_avoid = gr.Textbox(
                label="Must Avoid",
                placeholder="Comma-separated list (optional)",
            )
            required_mentions = gr.Textbox(
                label="Required Mentions",
                placeholder="Comma-separated list (optional)",
            )

        with gr.Group():
            gr.Markdown("## Stylistic Preferences")
            humor_level = gr.Dropdown(
                label="Humor Level",
                choices=["", "low", "medium", "high", "Custom"],
                value="",
            )
            humor_level_custom = gr.Textbox(label="Humor Level (Custom)", placeholder="Used when dropdown=Custom")
            formality = gr.Dropdown(
                label="Formality",
                choices=["", "informal", "neutral", "formal", "Custom"],
                value="",
            )
            formality_custom = gr.Textbox(label="Formality (Custom)", placeholder="Used when dropdown=Custom")
            narrative_voice = gr.Dropdown(
                label="Narrative Voice",
                choices=["", "first-person", "second-person", "third-person", "Custom"],
                value="",
            )
            narrative_voice_custom = gr.Textbox(
                label="Narrative Voice (Custom)", placeholder="Used when dropdown=Custom"
            )

        build_button = gr.Button("Build Intent")
        json_output = gr.Code(label="IntentEnvelope (JSON)", language="json")
        yaml_output = gr.Code(label="IntentEnvelope (YAML)", language="yaml")

        build_button.click(
            build_intent,
            inputs=[
                document_goal,
                audience,
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
            ],
            outputs=[json_output, yaml_output],
        )

    demo.launch()


if __name__ == "__main__":
    main()
