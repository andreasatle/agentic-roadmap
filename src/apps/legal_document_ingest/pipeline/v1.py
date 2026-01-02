"""Normative v1 contract pipeline. All other pipelines are deprecated and non-normative."""

from apps.legal_document_ingest.conditioning.views import spatial_ordered_token_ids
from apps.legal_document_ingest.contract.validate import (
    ContractValidationResult,
    validate_v1_contract,
)
from apps.legal_document_ingest.detection.anchors import detect_anchor_candidates
from apps.legal_document_ingest.detection.spans import expand_candidate_spans
from apps.legal_document_ingest.output.final import emit_final_legal_description
from apps.legal_document_ingest.output.trace import build_extraction_trace
from apps.legal_document_ingest.ocr.models import EvidenceBundle
from apps.legal_document_ingest.reconstruction.corrections import apply_allowed_corrections
from apps.legal_document_ingest.reconstruction.lines import reconstruct_lines
from apps.legal_document_ingest.scoring.heuristic import score_validated_spans
from apps.legal_document_ingest.selection.audit import build_selection_audit
from apps.legal_document_ingest.selection.simple import select_span
from apps.legal_document_ingest.uncertainty.detect import detect_uncertainties
from apps.legal_document_ingest.uncertainty.gate import (
    ExtractionContinuation,
    ExtractionFailure,
    apply_failure_gate,
)
from apps.legal_document_ingest.validation.structural import validate_candidate_spans


def run_extraction_v1(bundle: EvidenceBundle) -> ContractValidationResult:
    ordered_token_ids = spatial_ordered_token_ids(bundle)
    anchors = detect_anchor_candidates(bundle, ordered_token_ids)
    candidate_spans = expand_candidate_spans(bundle, ordered_token_ids, anchors)
    validated = validate_candidate_spans(bundle, ordered_token_ids, candidate_spans)
    scored = score_validated_spans(bundle, validated)
    selection = select_span(scored)
    audit = build_selection_audit(scored, selection)
    selected_token_ids = []
    if audit.selection_result.selected is not None:
        selected_token_ids = list(
            audit.selection_result.selected.validated.span.token_ids
        )
    reconstructed_lines = reconstruct_lines(bundle, selected_token_ids)
    corrected_lines = apply_allowed_corrections(reconstructed_lines)
    uncertainties = detect_uncertainties(bundle, corrected_lines)
    gate = apply_failure_gate(bundle, audit, corrected_lines, uncertainties)
    if isinstance(gate, ExtractionFailure):
        return validate_v1_contract(
            final_description=None,
            trace=None,
            failure=gate,
        )
    if isinstance(gate, ExtractionContinuation):
        final_description = emit_final_legal_description(gate, corrected_lines)
        trace = build_extraction_trace(
            audit,
            reconstructed_lines,
            corrected_lines,
            uncertainties,
        )
        return validate_v1_contract(
            final_description=final_description,
            trace=trace,
            failure=None,
        )
    raise TypeError("Unexpected extraction gate result.")
