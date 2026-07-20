"""HuggingFace transformer detector (dslim/bert-base-NER).

Same detector interface as the others: `load()` and `detect(model, text)`.

This is the second model of the required two-model comparison. It is fine-tuned on
CoNLL-2003, which has only four entity types, so it produces no dates and no money.
That limitation is part of the finding rather than a fault.
"""

from ..spans import Span
from ._hf import build, detect_with, device_index

MODEL_NAME = "dslim/bert-base-NER"

# Map CoNLL-2003 labels to the target scheme. MISC is too vague, so it is ignored.
LABEL_MAP = {
    "PER": "PERSON",
    "ORG": "ORG",
    "LOC": "LOCATION",
}

__all__ = ["LABEL_MAP", "MODEL_NAME", "detect", "device_index", "load"]


def load(model_name: str = MODEL_NAME):
    """Load the HuggingFace NER pipeline, on a GPU when one is usable."""
    return build(model_name)


def detect(model, text: str) -> list[Span]:
    """Return (start, end, label) spans for the targeted entities in `text`."""
    return detect_with(model, text, LABEL_MAP)
