
import pytest


from domain.document_writer.writer.schemas import DraftWorkerInput
from domain.document_writer.writer.types import DraftSectionTask


def test_worker_input_disallows_project_state():
    task = DraftSectionTask(node_id="Intro", section_name="Intro", purpose="p", requirements=["r"])
    with pytest.raises(Exception):
        DraftWorkerInput.model_validate({"task": task.model_dump(), "project_state": {"domain": {}}})
