
import pytest


from document_writer.domain.writer.schemas import WriterWorkerOutput
from document_writer.domain.writer.types import WriterResult


def test_worker_output_enforces_single_branch():
    valid = WriterWorkerOutput(result=WriterResult(text="ok"))
    assert valid.result.text == "ok"
    with pytest.raises(ValueError):
        WriterWorkerOutput(result=None, tool_request=None)
    with pytest.raises(ValueError):
        WriterWorkerOutput(result=WriterResult(text="x"), tool_request={"tool_name": "t", "args": {}})  # type: ignore[arg-type]
