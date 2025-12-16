
from domain.writer.state import StructureState
from domain.writer.schemas import WriterDomainState
from domain.writer.types import DraftSectionTask, WriterResult


def test_explicit_section_order_respected():
    structure = StructureState(sections=["Intro", "Body", "Conclusion"])
    state = WriterDomainState(structure=structure)
    # populate content
    for name in ["Intro", "Conclusion", "Body"]:
        task = DraftSectionTask(section_name=name, purpose="", requirements=[""])
        result = WriterResult(text=name)
        state = state.update(task, result)
    state.content.section_order = ["Conclusion", "Intro"]

    sections = state.content.sections
    order = state.content.section_order or state.structure.sections
    ordered = [sections[name] for name in order if name in sections]

    assert ordered == ["Conclusion", "Intro"]


def test_structure_order_used_when_section_order_absent():
    structure = StructureState(sections=["Intro", "Body", "Conclusion"])
    state = WriterDomainState(structure=structure)
    for name in ["Intro", "Body", "Conclusion"]:
        task = DraftSectionTask(section_name=name, purpose="", requirements=[""])
        result = WriterResult(text=name)
        state = state.update(task, result)

    sections = state.content.sections
    order = state.content.section_order or state.structure.sections
    ordered = [sections[name] for name in order if name in sections]

    assert ordered == ["Intro", "Body", "Conclusion"]
