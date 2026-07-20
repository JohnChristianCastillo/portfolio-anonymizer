"""HuggingFace transformer trained on OntoNotes, rather than CoNLL.

Added after the required two-model comparison, to answer a fair objection to it: the
CoNLL model loses partly because its label scheme has only four entity types, not
because the architecture is worse. This model is the same kind of transformer run
through the same pipeline, but trained on OntoNotes, so it can emit dates and money
and competes on the same ground as the spaCy pipeline.

No new dependency: only the model name and the label mapping differ.
"""

from ..spans import Span
from ._hf import build, detect_with

MODEL_NAME = "djagatiya/ner-roberta-base-ontonotesv5-englishv4"

# The same mapping used for spaCy, because both speak OntoNotes.
LABEL_MAP = {
    "PERSON": "PERSON",
    "ORG": "ORG",
    "GPE": "LOCATION",
    "LOC": "LOCATION",
    "DATE": "DATE_TIME",
    "TIME": "DATE_TIME",
    "MONEY": "AMOUNT",
}


def load(model_name: str = MODEL_NAME):
    """Load the OntoNotes NER pipeline."""
    return build(model_name)


def detect(model, text: str) -> list[Span]:
    """Return (start, end, label) spans for the targeted entities in `text`."""
    return detect_with(model, text, LABEL_MAP)
