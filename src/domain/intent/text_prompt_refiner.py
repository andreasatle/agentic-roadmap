"""
Text Prompt Refiner Contract

- Input: raw user text (str).
- Output: refined user text (str).
- Transformation is semantic-preserving, non-authoritative, and advisory-only.
- The refiner MUST NOT invent intent or meaning; it only normalizes the supplied text.
- The refiner does NOT plan, execute, extract intent, create structure, or generate documents.
"""
from pydantic import BaseModel


class TextPromptRefinerInput(BaseModel):
    """Raw user text input for the Text Prompt Refiner; sole, authority-free input."""

    text: str
