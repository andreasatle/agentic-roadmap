from openai import OpenAI

from agentic.agents import Agent
from agentic.problem.writer.schemas import WriterCriticInput, WriterCriticOutput
from agentic.problem.writer.state import WriterState


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
  "worker_answer": "<text the Worker wrote>"

  Optional:
  "project_state": {
    "project": { ... },
    "domain": { ... }
  } | null
}

OUTPUT FORMAT (STRICT JSON):
{
  "decision": "ACCEPT" | "REJECT",
  "feedback": "<actionable, minimal feedback or null>"
}

EVALUATION RULES:
1. **Section match**: The Worker’s text must be clearly and exclusively about the
   section named in the plan. If it drifts into other sections or meta-topics, REJECT.

2. **Purpose alignment**: The Worker’s text must fulfill the stated purpose.
   If the section exists to introduce the framework, it must introduce it.
   If the section exists to establish context, it must establish it.

3. **Requirements satisfaction**:
   - Every requirement must be satisfied.
   - Missing, incomplete, or ambiguous coverage → REJECT with targeted feedback.

4. **Tone and quality**:
   - Must read as a clear, coherent, publication-ready whitepaper section.
   - No reasoning traces, no meta-discussion, no JSON, no apology text.

5. **Scope containment**:
   - Worker must NOT add unrequested subsections, theories, or detours.
   - Worker must NOT anticipate future sections unless required by the task.

6. **Feedback policy**:
   - ACCEPT → "feedback": null.
   - REJECT → "feedback": a short, actionable correction list.
   - Feedback MUST be specific: “Expand requirement #2 with an example”,
     “Remove meta commentary”, “Clarify motivation”, etc.

7. **Strict JSON only**.
   No analysis, no commentary, no Markdown, no prose outside the JSON.

STATE USAGE:
- You may consider project_state to improve evaluation, but must operate correctly when it is null or missing.

Your job is deterministic evaluation. Nothing more.
"""


def make_critic(client: OpenAI, model: str) -> Agent[WriterCriticInput, WriterCriticOutput]:
    """
    MVP critic: accepts any non-empty text and mirrors the writer decision schema.
    """
    base_agent = Agent(
        name="WriterCritic",
        client=client,
        model=model,
        system_prompt=PROMPT_CRITIC,
        input_schema=WriterCriticInput,
        output_schema=WriterCriticOutput,
        temperature=0.0,
    )

    class WriterCriticAgent:
        def __init__(self, agent: Agent[WriterCriticInput, WriterCriticOutput]):
            self._agent = agent
            self.name = agent.name
            self.input_schema = agent.input_schema
            self.output_schema = agent.output_schema
            self.id = agent.id

        def __call__(self, user_input: str) -> str:
            critic_input = WriterCriticInput.model_validate_json(user_input)
            problem_state = getattr(critic_input, "problem_state", None)

            if isinstance(problem_state, WriterState):
                if critic_input.plan.section_name in problem_state.sections:
                    rejection = WriterCriticOutput(
                        decision="REJECT",
                        feedback="Section already exists in state; choose a new section name.",
                    )
                    return rejection.model_dump_json()

            return self._agent(user_input)

    return WriterCriticAgent(base_agent)  # type: ignore[return-value]
