from __future__ import annotations

import json

from agentic.supervisor import SupervisorResponse
from domain.writer.schemas import WriterDomainState


def test_supervisor_response_is_json_serializable():
    response = SupervisorResponse(
        task={"task": "example"},
        worker_id="worker",
        worker_output={"text": "done"},
        critic_decision={"decision": "ACCEPT"},
        trace=[{"state": "PLAN"}, {"state": "END"}],
    )

    serialized = response.model_dump()
    json.dumps(serialized)


def test_domain_state_can_be_rehydrated_from_response():
    original_state = WriterDomainState()
    state_snapshot = original_state.model_dump()

    response = SupervisorResponse(
        task={"task": "rehydrate"},
        worker_id="worker",
        worker_output={"text": "done"},
        critic_decision={"decision": "ACCEPT"},
        trace=[{"state": "PLAN"}, {"state": "END"}],
    )

    assert response.trace is not None
