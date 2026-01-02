"""Legacy pre-contract pipeline. Deprecated and non-normative.
Retained for backward compatibility only."""

from apps.legal_document_ingest.conditioning.views import spatial_ordered_token_ids
from apps.legal_document_ingest.detection.anchors import detect_anchor_candidates
from apps.legal_document_ingest.detection.spans import expand_candidate_spans
from apps.legal_document_ingest.output.result import build_extraction_result
from apps.legal_document_ingest.ocr.models import EvidenceBundle
from apps.legal_document_ingest.scoring.heuristic import score_validated_spans
from apps.legal_document_ingest.selection.audit import build_selection_audit
from apps.legal_document_ingest.selection.simple import select_span
from apps.legal_document_ingest.validation.structural import validate_candidate_spans


def run_extraction(bundle: EvidenceBundle):
    ordered_token_ids = spatial_ordered_token_ids(bundle)
    anchors = detect_anchor_candidates(bundle, ordered_token_ids)
    candidate_spans = expand_candidate_spans(bundle, ordered_token_ids, anchors)
    validated = validate_candidate_spans(bundle, ordered_token_ids, candidate_spans)
    scored = score_validated_spans(bundle, validated)
    selection = select_span(scored)
    audit = build_selection_audit(scored, selection)
    result = build_extraction_result(bundle, audit)
    return result
