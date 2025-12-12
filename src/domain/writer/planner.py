import json
from openai import OpenAI

from agentic.agents import Agent
from domain.writer.schemas import WriterPlannerInput, WriterPlannerOutput
from domain.writer.types import WriterTask
from domain.writer.state import WriterContentState


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
            planner_input = WriterPlannerInput.model_validate_json(user_input)
            try:
                raw_payload = json.loads(user_input)
            except Exception:
                raw_payload = {}
            raw = self._agent(user_input)
            try:
                payload = json.loads(raw)
            except Exception:
                return raw
            task_obj = None
            section_order = None
            match payload:
                case dict():
                    match payload.get("task"), payload.get("next_task"):
                        case dict() as t, _:
                            task_obj = t
                            task_key = "task"
                        case _, dict() as nt:
                            task_obj = nt
                            task_key = "next_task"
                        case _:
                            task_key = None
                    if task_obj is not None and "operation" not in task_obj:
                        task_obj["operation"] = "draft"
                        if task_key:
                            payload[task_key] = task_obj
                    section_order = payload.get("section_order")
                    raw = json.dumps(payload)
                case _:
                    pass
            try:
                output_model = self.output_schema.model_validate_json(raw)
            except Exception:
                return raw

            state = getattr(planner_input, "project_state", None)
            completed_sections: list[str] = []
            domain_state = None
            match state:
                case WriterContentState():
                    if getattr(state, "sections", None):
                        completed_sections = list(state.sections)
                case dict() as state_dict:
                    domain_state = state_dict.get("domain_state") or state_dict.get("domain")
                    match domain_state:
                        case dict() as domain_dict:
                            if domain_dict.get("completed_sections"):
                                completed_sections = list(domain_dict["completed_sections"])
                        case _:
                            if domain_state and getattr(domain_state, "completed_sections", None):
                                completed_sections = list(domain_state.completed_sections)
                case _:
                    domain_state = getattr(state, "state", None) if state is not None else None
                    if domain_state and getattr(domain_state, "completed_sections", None):
                        completed_sections = list(domain_state.completed_sections)

            preserved_section_order = None
            match domain_state:
                case dict() as domain_dict:
                    preserved_section_order = domain_dict.get("section_order")
                case _:
                    if domain_state:
                        preserved_section_order = getattr(domain_state, "section_order", None)

            if section_order is None:
                section_order = getattr(output_model, "section_order", None)

            base_task = getattr(planner_input, "task", None) or getattr(output_model, "task", None)
            if base_task is None:
                return raw
            section_name = base_task.section_name
            attempts = completed_sections.count(section_name)

            operation = "draft" if section_name not in completed_sections else "refine"

            default_section_order = [
                "Introduction",
                "Origin Story",
                "Architecture",
                "Meta-Reflection",
                "Conclusion",
            ]

            has_domain_state = domain_state is not None
            is_first_call = has_domain_state and preserved_section_order is None

            if section_order is None:
                if is_first_call:
                    section_order = default_section_order
                elif preserved_section_order:
                    section_order = preserved_section_order

            new_task = WriterTask(
                section_name=section_name,
                purpose=base_task.purpose,
                requirements=base_task.requirements,
                operation=operation,
            )
            output_model.task = new_task
            output_model.section_order = section_order

            return output_model.model_dump_json()

    return WriterPlannerAgent(base_agent)  # type: ignore[return-value]
