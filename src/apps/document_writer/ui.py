import tempfile
from pathlib import Path
from typing import Any
from dotenv import load_dotenv
import gradio as gr
import yaml
from pydantic import ValidationError

from apps.document_writer.service import generate_document
from domain.intent import load_intent_from_file
from domain.intent.types import IntentEnvelope

load_dotenv(override=True)


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


def _intent_from_inputs(
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
) -> IntentEnvelope:
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
    return IntentEnvelope.model_validate(data)


def intent_to_ui(intent: IntentEnvelope) -> list[Any]:
    structural = intent.structural_intent
    semantic = intent.semantic_constraints
    style = intent.stylistic_preferences

    def _select_with_custom(value: str | None, choices: list[str]) -> tuple[str, str]:
        if value and value in choices:
            return value, ""
        if value:
            return "Custom", value
        return "", ""

    audience_choice, audience_custom = _select_with_custom(
        structural.audience, ["general", "executives", "engineers", "researchers"]
    )
    humor_choice, humor_custom = _select_with_custom(style.humor_level, ["none", "light", "moderate"])
    formality_choice, formality_custom = _select_with_custom(style.formality, ["informal", "neutral", "formal"])
    narrative_choice, narrative_custom = _select_with_custom(
        style.narrative_voice, ["first-person", "third-person", "neutral"]
    )

    return [
        structural.document_goal or "",
        audience_choice,
        audience_custom,
        structural.tone or "",
        "\n".join(structural.required_sections or []),
        "\n".join(structural.forbidden_sections or []),
        "\n".join(semantic.must_include or []),
        "\n".join(semantic.must_avoid or []),
        "\n".join(semantic.required_mentions or []),
        humor_choice,
        humor_custom,
        formality_choice,
        formality_custom,
        narrative_choice,
        narrative_custom,
    ]


def load_intent_into_ui(file_path: str | None) -> tuple[Any, ...]:
    if not file_path:
        return (
            gr.update(value=""),
            gr.update(value=""),
            gr.update(value=""),
            gr.update(value=""),
            gr.update(value=""),
            gr.update(value=""),
            gr.update(value=""),
            gr.update(value=""),
            gr.update(value=""),
            gr.update(value=""),
            gr.update(value=""),
            gr.update(value=""),
            gr.update(value=""),
            gr.update(value=""),
            gr.update(value=""),
            gr.update(value="No file provided."),
        )
    try:
        intent = load_intent_from_file(file_path)
    except Exception as exc:
        return (
            gr.update(value=""),
            gr.update(value=""),
            gr.update(value=""),
            gr.update(value=""),
            gr.update(value=""),
            gr.update(value=""),
            gr.update(value=""),
            gr.update(value=""),
            gr.update(value=""),
            gr.update(value=""),
            gr.update(value=""),
            gr.update(value=""),
            gr.update(value=""),
            gr.update(value=""),
            gr.update(value=""),
            gr.update(value=f"Intent load error: {exc}"),
        )
    values = intent_to_ui(intent)
    updates = [gr.update(value=v) for v in values]
    updates.append(gr.update(value=""))
    return tuple(updates)


def save_intent_yaml(
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
    filename: str,
) -> tuple[str | None, str]:
    try:
        intent = _intent_from_inputs(
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
        )
    except ValidationError as exc:
        return None, f"Validation error: {exc}"

    yaml_text = yaml.safe_dump(intent.model_dump(), sort_keys=False, default_flow_style=False)
    target_name = filename.strip() or "intent.yaml"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=f"-{target_name}")
    Path(tmp.name).write_text(yaml_text)
    return tmp.name, ""


def save_article(markdown: str, filename: str) -> tuple[str | None, str]:
    if not markdown or not markdown.strip():
        return None, "No article generated."
    target_name = filename.strip() or "article.md"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=f"-{target_name}")
    Path(tmp.name).write_text(markdown)
    return tmp.name, ""


def generate_article(
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
) -> tuple[str, str, str, gr.update]:
    try:
        intent = _intent_from_inputs(
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
        )
    except ValidationError as exc:
        return "", f"Validation error: {exc}", "", gr.update(interactive=False)

    try:
        result = generate_document(
            goal=intent.structural_intent.document_goal,
            audience=intent.structural_intent.audience,
            tone=intent.structural_intent.tone,
            intent=intent,
            trace=False,
        )
    except Exception as exc:
        return "", f"Execution error: {exc}", "", gr.update(interactive=False)

    return result.markdown, "", result.markdown, gr.update(interactive=True)
def main() -> None:
    with gr.Blocks(title="Document Intent") as demo:
        gr.Markdown("# Document Intent")
        intent_file = gr.File(label="Intent YAML", type="filepath", file_types=[".yaml", ".yml"])
        article_state = gr.State("")

        with gr.Group():
            gr.Markdown("Load an existing IntentEnvelope (optional)")
            intent_file

        with gr.Group():
            gr.Markdown("## Intent Definition")
            with gr.Group():
                gr.Markdown("### Structural Intent")
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
                gr.Markdown("### Semantic Constraints")
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
                gr.Markdown("### Stylistic Preferences")
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

        with gr.Group():
            gr.Markdown("## Save Intent")
            with gr.Row():
                filename_input = gr.Textbox(
                    label="Intent file name", placeholder="intent.yaml", value="intent.yaml", scale=2
                )
                save_intent_button = gr.Button("Save Intent", scale=1)
                intent_download = gr.File(label="Intent YAML (download)", interactive=False, scale=2)

        with gr.Group():
            gr.Markdown("## Generate Article")
            generate_button = gr.Button("Generate Article")

        with gr.Group():
            gr.Markdown("## Generated Article")
            article_output = gr.Code(label="Generated Article", language="markdown")

        with gr.Group():
            gr.Markdown("## Save Article")
            with gr.Row():
                article_filename_input = gr.Textbox(
                    label="Article file name", placeholder="article.md", value="article.md", scale=2
                )
                save_article_button = gr.Button("Save Article", interactive=False, scale=1)
                article_download = gr.File(label="Article (download)", interactive=False, scale=2)

        with gr.Group():
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

        intent_file.change(
            load_intent_into_ui,
            inputs=[intent_file],
            outputs=inputs + [error_output],
        )

        save_intent_button.click(
            save_intent_yaml,
            inputs=inputs + [filename_input],
            outputs=[intent_download, error_output],
        )

        generate_button.click(
            generate_article,
            inputs=inputs,
            outputs=[article_output, error_output, article_state, save_article_button],
        )

        save_article_button.click(
            save_article,
            inputs=[article_state, article_filename_input],
            outputs=[article_download, error_output],
        )

    demo.launch()


if __name__ == "__main__":
    main()
