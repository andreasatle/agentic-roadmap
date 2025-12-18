from agentic.agents.openai import OpenAIAgent
from domain.writer.schemas import WriterCriticInput, WriterCriticOutput


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

            # Requirement coverage
            for req in getattr(critic_input.plan, "requirements", []) or []:
                if req and req.lower() not in lower_text:
                    return WriterCriticOutput(
                        decision="REJECT",
                        feedback={
                            "kind": "TASK_INCOMPLETE",
                            "message": f"Add coverage for requirement: '{req}'.",
                        },
                    ).model_dump_json()

            # Scope containment
            if section_name and section_name.lower() not in lower_text:
                return WriterCriticOutput(
                    decision="REJECT",
                    feedback={
                        "kind": "SCOPE_ERROR",
                        "message": f"Focus on section '{section_name}' explicitly.",
                    },
                ).model_dump_json()
            if node_desc and node_desc.lower() not in lower_text:
                return WriterCriticOutput(
                    decision="REJECT",
                    feedback={
                        "kind": "SCOPE_ERROR",
                        "message": "Align text with the section description; remove off-topic content.",
                    },
                ).model_dump_json()
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

            return WriterCriticOutput(
                decision="ACCEPT",
                feedback=None,
            ).model_dump_json()

    return WriterCriticAgent(base_agent)  # type: ignore[return-value]
