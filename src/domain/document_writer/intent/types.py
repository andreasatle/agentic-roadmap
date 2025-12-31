"""
Layer 2 Intent Envelope.

This module captures interpreted user intent in a non-executable, contract-only container.
It is NOT responsible for planning, execution, traversal, or inference. Downstream layers
may project subsets of this data, but this module itself remains passive and domain-agnostic.
"""
from typing import List, Optional

from pydantic import BaseModel, Field


class StructuralIntent(BaseModel):
    """Signals that may influence document structure; not executable instructions."""

    document_goal: Optional[str] = Field(
        default=None, description="High-level goal of the document; not a plan."
    )
    audience: Optional[str] = Field(
        default=None, description="Target audience description; does not imply structure."
    )
    tone: Optional[str] = Field(
        default=None, description="Desired tone (e.g., formal); advisory only."
    )
    required_sections: List[str] = Field(
        default_factory=list,
        description="Section labels the user expects; does not create structure by itself.",
    )
    forbidden_sections: List[str] = Field(
        default_factory=list,
        description="Section labels to avoid; does not delete or reorder structure by itself.",
    )


class GlobalSemanticConstraints(BaseModel):
    """Placement-agnostic constraints; no structural implications."""

    must_include: List[str] = Field(
        default_factory=list,
        description="Concepts or facts that must appear somewhere; no placement implied.",
    )
    must_avoid: List[str] = Field(
        default_factory=list,
        description="Concepts or phrases to exclude globally; no placement implied.",
    )
    required_mentions: List[str] = Field(
        default_factory=list,
        description="Entities or topics to mention; not bound to specific sections.",
    )


class StylisticPreferences(BaseModel):
    """Soft, non-binding stylistic preferences."""

    humor_level: Optional[str] = Field(
        default=None, description="Desired humor level; advisory, non-binding."
    )
    formality: Optional[str] = Field(
        default=None, description="Desired formality level; advisory, non-binding."
    )
    narrative_voice: Optional[str] = Field(
        default=None, description="Preferred narrative voice (e.g., first-person); advisory only."
    )


class IntentEnvelope(BaseModel):
    """Top-level container for user intent; groups signals without interpretation or execution."""

    structural_intent: StructuralIntent = Field(
        default_factory=StructuralIntent,
        description="Potential structural signals; not a plan and not executable.",
    )
    semantic_constraints: GlobalSemanticConstraints = Field(
        default_factory=GlobalSemanticConstraints,
        description="Placement-agnostic constraints; do not imply structure or execution.",
    )
    stylistic_preferences: StylisticPreferences = Field(
        default_factory=StylisticPreferences,
        description="Soft style preferences; advisory only and non-binding.",
    )
