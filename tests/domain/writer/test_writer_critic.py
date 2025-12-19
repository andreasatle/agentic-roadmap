import pytest

from domain.writer.critic import make_critic
from domain.writer.schemas import WriterCriticInput, WriterCriticOutput
from domain.writer.types import DraftSectionTask, WriterResult


def _critic():
    return make_critic(model="test-model")


def test_writer_critic_accepts_valid_section():
    critic = _critic()
    plan = DraftSectionTask(
        node_id="perf-1",
        section_name="Performance",
        purpose="Describe system performance characteristics.",
        requirements=["Include latency benchmarks."],
    )
    text = (
        "Performance section details describe system performance characteristics. "
        "It includes latency benchmarks and discusses throughput, scalability, and constraints "
        "across expected workloads."
    )
    payload = WriterCriticInput(plan=plan, worker_answer=WriterResult(text=text))
    result = WriterCriticOutput.model_validate_json(critic(payload.model_dump_json()))
    assert result.decision == "ACCEPT"
    assert result.feedback is None


def test_writer_critic_rejects_missing_requirement():
    critic = _critic()
    plan = DraftSectionTask(
        node_id="perf-1",
        section_name="Performance",
        purpose="Describe system performance characteristics.",
        requirements=["Detail failure modes."],
    )
    text = (
        "The Performance section describes system performance characteristics, "
        "covering latency expectations and throughput benchmarks across typical loads."
    )
    payload = WriterCriticInput(plan=plan, worker_answer=WriterResult(text=text))
    result = WriterCriticOutput.model_validate_json(critic(payload.model_dump_json()))
    assert result.decision == "REJECT"
    assert result.feedback is not None
    assert result.feedback.kind == "TASK_INCOMPLETE"


def test_writer_critic_rejects_scope_error_when_section_missing():
    critic = _critic()
    plan = DraftSectionTask(
        node_id="avail-1",
        section_name="Availability",
        purpose="Explain availability posture.",
        requirements=["Cover availability targets."],
    )
    text = (
        "This section explains availability posture and covers availability targets for the service. "
        "It also notes operational playbooks and recovery objectives."
    )
    payload = WriterCriticInput(plan=plan, worker_answer=WriterResult(text=text))
    result = WriterCriticOutput.model_validate_json(critic(payload.model_dump_json()))
    assert result.decision == "REJECT"
    assert result.feedback is not None
    assert result.feedback.kind == "SCOPE_ERROR"


def test_writer_critic_rejects_placeholder_content():
    critic = _critic()
    plan = DraftSectionTask(
        node_id="sec-1",
        section_name="Overview",
        purpose="Provide the overview of the system.",
        requirements=["Mention system purpose."],
    )
    text = (
        "Overview section TODO: provide the overview of the system and mention system purpose. "
        "This placeholder will be replaced later."
    )
    payload = WriterCriticInput(plan=plan, worker_answer=WriterResult(text=text))
    result = WriterCriticOutput.model_validate_json(critic(payload.model_dump_json()))
    assert result.decision == "REJECT"
    assert result.feedback is not None
    assert result.feedback.kind == "TASK_INCOMPLETE"


def test_writer_critic_rejects_too_short_text():
    critic = _critic()
    plan = DraftSectionTask(
        node_id="sec-2",
        section_name="Security",
        purpose="Describe security posture.",
        requirements=["Note encryption measures."],
    )
    text = "Security section describes security posture and notes encryption measures."
    payload = WriterCriticInput(plan=plan, worker_answer=WriterResult(text=text))
    result = WriterCriticOutput.model_validate_json(critic(payload.model_dump_json()))
    assert result.decision == "REJECT"
    assert result.feedback is not None
    assert result.feedback.kind == "TASK_INCOMPLETE"
