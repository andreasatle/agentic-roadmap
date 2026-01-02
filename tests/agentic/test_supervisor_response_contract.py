
import json

from agentic.controller import ControllerResponse


def test_supervisor_response_is_json_serializable():
    response = ControllerResponse(
        task={"task": "example"},
        worker_id="worker",
        worker_output={"text": "done"},
        critic_decision={"decision": "ACCEPT"},
        trace=[{"state": "PLAN"}, {"state": "END"}],
    )

    serialized = response.model_dump()
    json.dumps(serialized)


def test_supervisor_response_has_trace_but_no_domain_state():
    response = ControllerResponse(
        task={"task": "rehydrate"},
        worker_id="worker",
        worker_output={"text": "done"},
        critic_decision={"decision": "ACCEPT"},
        trace=[{"state": "PLAN"}, {"state": "END"}],
    )

    assert response.trace is not None
    assert "domain_state" not in response.model_dump()
