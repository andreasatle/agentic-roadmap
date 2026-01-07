import re

from agentic_workflow.agents.openai import OpenAIAgent
from agentic_workflow.logging_config import get_logger
from document_writer.domain.writer.schemas import WriterCriticInput, WriterCriticOutput


PROMPT_CRITIC = """ROLE:
You are the Critic in a Planner–Worker–Critic loop.

Your ONLY responsibility is to evaluate whether the Worker’s written section
satisfies the Planner’s task specification. You do not propose new content,
you do not write sections, and you do not modify tasks. You judge compliance.

INPUT FORMAT:
{
  "plan": {
    "section_name": "<name>",
    "purpose": "<reason>",
    "requirements": ["...", "..."]
  },
  "worker_answer": "<text the Worker wrote>",
  "node_description": "<semantic obligation for this section>"
}

OUTPUT FORMAT (STRICT JSON):
{
  "decision": "ACCEPT" | "REJECT",
  "feedback": null | {
    "kind": "<EMPTY_RESULT | TASK_INCOMPLETE | SCOPE_ERROR | OTHER>",
    "message": "<actionable, minimal feedback>"
  }
}

EVALUATION RULES:
1. **Section match**: The Worker’s text must be clearly and exclusively about the
   section named in the plan. If it drifts into other sections or meta-topics, REJECT.

2. **Purpose alignment**: The Worker’s text must fulfill the stated purpose and the semantic
   obligation described by node_description. If it fails to cover that described topic
   or drifts away from it, REJECT.

3. **Requirements satisfaction**:
   - Every requirement must be satisfied.
   - Missing, incomplete, or ambiguous coverage → REJECT with targeted feedback.

4. **Tone and quality**:
   - Must read as a clear, coherent, publication-ready whitepaper section.
   - No reasoning traces, no meta-discussion, no JSON, no apology text.

5. **Scope containment**:
   - Worker must NOT add unrequested subsections, theories, detours, or unrelated topics.
   - Worker must NOT anticipate future sections unless required by the task or node_description.

6. **Feedback policy**:
   - ACCEPT → feedback = null.
   - REJECT → feedback must be an object with kind and message.
   - Use kind="EMPTY_RESULT" for missing/empty text, "TASK_INCOMPLETE" for unmet requirements, "SCOPE_ERROR" for off-topic content, "OTHER" otherwise.
   - Feedback.message MUST be specific: “Expand requirement #2 with an example”,
     “Remove meta commentary”, “Clarify motivation”, etc.

7. **Strict JSON only**.
   No analysis, no commentary, no Markdown, no prose outside the JSON.

Your job is deterministic evaluation. Nothing more.
"""


def make_critic(model: str) -> OpenAIAgent[WriterCriticInput, WriterCriticOutput]:
    """
    MVP critic: accepts any non-empty text and mirrors the writer decision schema.
    """
    logger = get_logger("WriterCritic")

    base_agent = OpenAIAgent(
        name="WriterCritic",
        model=model,
        system_prompt=PROMPT_CRITIC,
        input_schema=WriterCriticInput,
        output_schema=WriterCriticOutput,
        temperature=0.0,
    )

    class WriterCriticAgent:
        def __init__(self, agent: OpenAIAgent[WriterCriticInput, WriterCriticOutput]):
            self._agent = agent
            self.name = agent.name
            self.input_schema = agent.input_schema
            self.output_schema = agent.output_schema
            self.id = agent.id

        def __call__(self, user_input: str) -> str:
            critic_input = WriterCriticInput.model_validate_json(user_input)
            text = critic_input.worker_answer.text if critic_input.worker_answer else ""

            if not text.strip():
                return WriterCriticOutput(
                    decision="REJECT",
                    feedback={
                        "kind": "EMPTY_RESULT",
                        "message": "Worker produced empty text.",
                    },
                ).model_dump_json()

            lower_text = text.lower()
            section_name = getattr(critic_input.plan, "section_name", "") or ""
            node_desc = critic_input.node_description or getattr(critic_input.plan, "purpose", "")
            applies_thesis_rule = getattr(critic_input.plan, "applies_thesis_rule", False)

            # Requirement coverage via semantic overlap (conceptual, not verbatim).
            def requirement_satisfied(req: str, body: str) -> bool:
                req_terms = {t for t in re.findall(r"\w+", req.lower()) if len(t) > 3}
                if not req_terms:
                    return False
                body_terms = set(re.findall(r"\w+", body.lower()))
                overlap = req_terms & body_terms
                return len(overlap) >= max(2, len(req_terms) // 3)

            for req in getattr(critic_input.plan, "requirements", []) or []:
                if not requirement_satisfied(req, text):
                    return WriterCriticOutput(
                        decision="REJECT",
                        feedback={
                            "kind": "TASK_INCOMPLETE",
                            "message": f"Missing semantic coverage of requirement: '{req}'.",
                        },
                    ).model_dump_json()

            # Completeness heuristics
            if len(text.strip()) < 80:
                return WriterCriticOutput(
                    decision="REJECT",
                    feedback={
                        "kind": "TASK_INCOMPLETE",
                        "message": "Expand the section with substantive prose; current text is too short.",
                    },
                ).model_dump_json()
            lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
            if lines:
                bullet_lines = [ln for ln in lines if ln.startswith(("-", "*", "•"))]
                if len(bullet_lines) > len(lines) / 2:
                    return WriterCriticOutput(
                        decision="REJECT",
                        feedback={
                            "kind": "TASK_INCOMPLETE",
                            "message": "Convert bullet fragments into cohesive prose paragraphs.",
                        },
                ).model_dump_json()
            placeholder_terms = ["todo", "tbd", "lorem", "ipsum", "placeholder"]
            for term in placeholder_terms:
                if term in lower_text:
                    return WriterCriticOutput(
                        decision="REJECT",
                        feedback={
                            "kind": "TASK_INCOMPLETE",
                            "message": "Replace placeholder text with completed section prose.",
                        },
                    ).model_dump_json()

            def _extract_thesis(plan) -> str | None:
                """Pull a labeled thesis from plan fields, if present."""
                search_fields = []
                if hasattr(plan, "purpose"):
                    search_fields.append(getattr(plan, "purpose"))
                search_fields.extend(getattr(plan, "requirements", []) or [])
                for field in search_fields:
                    if not field:
                        continue
                    match = re.search(r"(?i)thesis\s*:\s*(.+)", field)
                    if match:
                        thesis_text = match.group(1).strip()
                        thesis_text = thesis_text.splitlines()[0].strip()
                        return thesis_text
                return None

            def _thesis_present(thesis: str, body: str) -> bool:
                if not thesis:
                    return False
                if thesis in body:
                    return True
                thesis_terms = {t for t in re.findall(r"\w+", thesis.lower()) if len(t) > 3}
                if not thesis_terms:
                    return False
                sentences = re.split(r"(?<=[.!?])\s+", body)
                for sentence in sentences:
                    terms = set(re.findall(r"\w+", sentence.lower()))
                    if len(thesis_terms & terms) >= max(3, len(thesis_terms) // 2):
                        return True
                return False

            def _candidate_thesis_sentences(body: str) -> list[str]:
                sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", body) if s.strip()]
                markers = [
                    "thesis",
                    "argues",
                    "contends",
                    "asserts",
                    "central claim",
                    "main claim",
                    "this essay",
                    "this article",
                ]
                return [s for s in sentences if any(m in s.lower() for m in markers)]

            def _is_list_like(sentence: str) -> bool:
                # List-like if it enumerates 3+ segments separated by commas/semicolons/and.
                segments = [seg.strip() for seg in re.split(r",|;|\band\b", sentence) if seg.strip()]
                return len(segments) >= 3

            if applies_thesis_rule:
                thesis_text = _extract_thesis(critic_input.plan)
                if thesis_text:
                    logger.debug("writer_critic_thesis_extracted", extra={"thesis": thesis_text})
                section_lower = section_name.lower()
                is_intro = section_lower.startswith("intro")
                is_conclusion = "conclusion" in section_lower

                if thesis_text and (is_intro or is_conclusion):
                    candidates = _candidate_thesis_sentences(text)
                    if is_intro:
                        if not _thesis_present(thesis_text, text):
                            return WriterCriticOutput(
                                decision="REJECT",
                                feedback={
                                    "kind": "MISSING_THESIS",
                                    "message": "State the single thesis explicitly in the introduction.",
                                },
                            ).model_dump_json()
                        if len(candidates) > 1:
                            return WriterCriticOutput(
                                decision="REJECT",
                                feedback={
                                    "kind": "WEAK_THESIS",
                                    "message": "Keep exactly one thesis; remove competing claims in the introduction.",
                                },
                            ).model_dump_json()
                        if candidates:
                            thesis_sentence = candidates[0]
                            if len(thesis_sentence.split()) < 8 or _is_list_like(thesis_sentence):
                                return WriterCriticOutput(
                                    decision="REJECT",
                                    feedback={
                                        "kind": "WEAK_THESIS",
                                        "message": "Strengthen the thesis into a single declarative central claim.",
                                    },
                                ).model_dump_json()
                    if is_conclusion:
                        if not _thesis_present(thesis_text, text):
                            return WriterCriticOutput(
                                decision="REJECT",
                                feedback={
                                    "kind": "MISSING_THESIS",
                                    "message": "Revisit the thesis in the conclusion; make the connection explicit.",
                                },
                            ).model_dump_json()
                        if thesis_text in text:
                            return WriterCriticOutput(
                                decision="REJECT",
                                feedback={
                                    "kind": "WEAK_THESIS",
                                    "message": "Paraphrase the thesis in the conclusion; do not repeat it verbatim.",
                                },
                            ).model_dump_json()

            def _has_section_identity(name: str, body: str) -> bool:
                if not name:
                    return True
                escaped = re.escape(name)
                patterns = [
                    rf"(?mi)^\s*#{{1,6}}\s*{escaped}\b",  # Markdown heading
                    rf"(?mi)^\s*{escaped}\s*:",          # Label style
                    rf"(?i)\b{escaped}\s+section\b",     # Phrase style
                ]
                return any(re.search(pat, body) for pat in patterns)

            # Scope containment: enforce exclusions, not literal inclusion.
            forbidden_scope_terms = [
                "future section",
                "next section",
                "other sections",
                "entire document",
                "whole document",
                "overall document",
                "document-wide",
                "conclusion of the document",
            ]
            for term in forbidden_scope_terms:
                if term in lower_text:
                    return WriterCriticOutput(
                        decision="REJECT",
                        feedback={
                            "kind": "SCOPE_ERROR",
                            "message": f"Remove meta or cross-section content (found '{term}').",
                        },
                    ).model_dump_json()
            for term in getattr(critic_input.plan, "forbidden_terms", []) or []:
                if term and term.lower() in lower_text:
                    return WriterCriticOutput(
                        decision="REJECT",
                        feedback={
                            "kind": "SCOPE_ERROR",
                            "message": f"Remove forbidden term: '{term}'.",
                        },
                    ).model_dump_json()

            if not _has_section_identity(section_name, text):
                return WriterCriticOutput(
                    decision="REJECT",
                    feedback={
                        "kind": "SCOPE_ERROR",
                        "message": f"Section identity missing: add a heading or label for '{section_name}'.",
                    },
                ).model_dump_json()

            return WriterCriticOutput(
                decision="ACCEPT",
                feedback=None,
            ).model_dump_json()

    return WriterCriticAgent(base_agent)  # type: ignore[return-value]
