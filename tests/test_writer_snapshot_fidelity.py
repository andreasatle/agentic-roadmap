
import pytest


from domain.writer.schemas import WriterWorkerInput
from domain.writer.types import DraftSectionTask


def test_worker_input_disallows_project_state():
    task = DraftSectionTask(section_name="Intro", purpose="p", requirements=["r"])
    with pytest.raises(Exception):
        WriterWorkerInput.model_validate({"task": task.model_dump(), "project_state": {"domain": {}}})
