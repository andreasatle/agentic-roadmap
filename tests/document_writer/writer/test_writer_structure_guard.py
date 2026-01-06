
import sys

import pytest

from document_writer.domain.writer.main import main as writer_main


def test_writer_raises_without_structure(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["prog"])
    with pytest.raises(RuntimeError):
        writer_main()
