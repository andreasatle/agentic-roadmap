from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from apps.legal_document_ingest.output.final import FinalLegalDescription
from apps.legal_document_ingest.output.trace import ExtractionTrace
from apps.legal_document_ingest.uncertainty.gate import ExtractionFailure


class ContractValidationPass(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    status: Literal["PASS"]
    final_description: FinalLegalDescription
    trace: ExtractionTrace


class ContractValidationFailure(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    status: Literal["FAIL"]
    reason: str


ContractValidationResult = ContractValidationPass | ContractValidationFailure


def validate_v1_contract(
    *,
    final_description: FinalLegalDescription | None,
    trace: ExtractionTrace | None,
    failure: ExtractionFailure | None,
) -> ContractValidationResult:
    present = sum(
        1 for item in (final_description, failure) if item is not None
    )
    if present != 1:
        return ContractValidationFailure(
            status="FAIL",
            reason="INVALID_OUTCOME_COMBINATION",
        )

    if final_description is not None:
        if trace is None:
            return ContractValidationFailure(
                status="FAIL",
                reason="MISSING_TRACE",
            )
        if not final_description.text:
            return ContractValidationFailure(
                status="FAIL",
                reason="EMPTY_FINAL_TEXT",
            )
        if not trace.selected_span_token_ids:
            return ContractValidationFailure(
                status="FAIL",
                reason="MISSING_SELECTED_SPAN_TOKENS",
            )
        allowed_types = {
            "SYMBOL_REPAIR",
            "HYPHENATION_REPAIR",
            "LEXICON_FIX",
        }
        for record in trace.corrections:
            if record.type not in allowed_types:
                return ContractValidationFailure(
                    status="FAIL",
                    reason="INVALID_CORRECTION_TYPE",
                )
            if not record.token_ids:
                return ContractValidationFailure(
                    status="FAIL",
                    reason="MISSING_CORRECTION_TOKENS",
                )
        for record in trace.uncertainties:
            if not record.token_ids:
                return ContractValidationFailure(
                    status="FAIL",
                    reason="MISSING_UNCERTAINTY_TOKENS",
                )
        if trace.uncertainties:
            return ContractValidationFailure(
                status="FAIL",
                reason="UNCERTAINTIES_PRESENT",
            )
        return ContractValidationPass(
            status="PASS",
            final_description=final_description,
            trace=trace,
        )

    if failure is None:
        return ContractValidationFailure(
            status="FAIL",
            reason="MISSING_FAILURE",
        )
    if failure.status != "FAIL":
        return ContractValidationFailure(
            status="FAIL",
            reason="INVALID_FAILURE_STATUS",
        )
    if not failure.reason:
        return ContractValidationFailure(
            status="FAIL",
            reason="EMPTY_FAILURE_REASON",
        )
    if failure.uncertainties is None:
        return ContractValidationFailure(
            status="FAIL",
            reason="MISSING_FAILURE_UNCERTAINTIES",
        )
    return ContractValidationFailure(
        status="FAIL",
        reason=failure.reason,
    )
