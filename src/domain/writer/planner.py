import json
from openai import OpenAI

from agentic.agents import Agent
from domain.writer.schemas import WriterPlannerInput, WriterPlannerOutput
from domain.writer.types import WriterTask
from domain.writer.state import StructureState, WriterContentState


PROMPT_PLANNER = """ROLE:
You are the Planner in a Planner–Worker–Critic loop.

Your responsibility is to decompose a high-level writing goal into a single,
precise subtask for the Worker. You do not write prose. You do not invent
content. You do not execute. You decide WHAT should be written next and WHY.

You must treat the provided topic and constraints as authoritative.

INPUT (FROM SUPERVISOR / CLI):
{
  "topic": "<primary subject to write about>",
  "tone": "<optional: academic | technical | informal | neutral | etc.>",
  "audience": "<optional: general | expert | developer | student | etc.>",
  "length": "<optional: short | medium | long>",
  "project_state": {
    "project": { ... },   // global ProjectState snapshot
    "domain": { ... }     // writer-specific state snapshot
  } | null
}

SEMANTIC AUTHORITY RULES:
1. The topic defines the subject matter. You must not override it.
2. Do not introduce frameworks, theories, examples, or narratives unless they
   naturally follow from the topic.
3. If the topic is broad or abstract, choose a neutral anchoring section.
4. If the topic is technical, anchor with definitions or scope.
5. If the topic is narrative or philosophical, anchor with framing context.

STRUCTURAL RESPONSIBILITIES:
- Decide the FIRST section to write.
- Choose a section that logically anchors the entire article.
- Ensure the section is appropriate given topic, tone, and audience.
- Avoid repetition based on project_state if present.

PLANNER OUTPUT FORMAT (STRICT JSON ONLY):
{
  "task": {
    "section_name": "<concise, human-readable section title>",
    "purpose": "<why this section is necessary for the article>",
    "operation": "draft | refine",
    "requirements": [
      "<concrete acceptance criterion 1>",
      "<concrete acceptance criterion 2>",
      "<etc>"
    ]
  },
  "section_order": [
    "<optional: proposed high-level section order>"
  ]
}

RULES:
1. Produce exactly ONE task.
2. Do not write content or examples.
3. Do not mention specific frameworks unless implied by the topic.
4. Requirements must be testable and minimal.
5. If content does not directly follow from the provided topic, it must not be introduced.
6. Output JSON only. No commentary.

STATE USAGE:
- If project_state.domain contains completed sections, do not repeat them.
- If project_state.project contains previous plans or results, continue logically.
- If project_state is null, behave identically with no assumptions.

Generate the first plan now.
"""


def make_planner(client: OpenAI, model: str) -> Agent[WriterPlannerInput, WriterPlannerOutput]:
    """
    MVP planner: emits a single WriterTask routed to the writer worker.
    """
    base_agent = Agent(
        name="WriterPlanner",
        client=client,
        model=model,
        system_prompt=PROMPT_PLANNER,
        input_schema=WriterPlannerInput,
        output_schema=WriterPlannerOutput,
        temperature=0.0,
    )

    class WriterPlannerAgent:
        def __init__(self, agent: Agent[WriterPlannerInput, WriterPlannerOutput]):
            self._agent = agent
            self.name = agent.name
            self.input_schema = agent.input_schema
            self.output_schema = agent.output_schema
            self.id = agent.id

        def __call__(self, user_input: str) -> str:
            planner_input = self.input_schema.model_validate_json(user_input)
            project_state = planner_input.project_state or {}
            domain_state = project_state.get("domain_state") or {}
            structure_data = domain_state.get("structure")
            completed_sections = domain_state.get("completed_sections") or []
            if structure_data is None:
                raise RuntimeError("StructureState is required for writer planning.")
            structure = StructureState.model_validate(structure_data)
            if not structure.sections:
                raise RuntimeError("StructureState must include sections for writer planning.")
            next_section = structure.next_section(completed_sections)
            if not next_section:
                output_model = WriterPlannerOutput(
                    task=WriterTask(
                        section_name="__complete__",
                        purpose="Structure exhausted; no work remaining.",
                        operation="draft",
                        requirements=[],
                    ),
                    worker_id="writer-complete",
                    section_order=structure.sections,
                )
            else:
                task = WriterTask(
                    section_name=next_section,
                    purpose=f"Write the '{next_section}' section.",
                    operation="draft",
                    requirements=[],
                )
                output_model = WriterPlannerOutput(
                    task=task,
                    worker_id="writer-worker",
                    section_order=structure.sections,
                )
            return output_model.model_dump_json()

    return WriterPlannerAgent(base_agent)  # type: ignore[return-value]
