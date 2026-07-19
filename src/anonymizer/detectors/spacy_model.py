"""spaCy detector: detect entities and map them to the 12-label scheme.

Detector interface: `detect(model, text) -> list[Span]`.
"""

import spacy

from ..spans import Span

MODEL_NAME = "en_core_web_sm"

# Map spaCy's OntoNotes labels to the target scheme. Unlisted labels are ignored.
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
    """Load the spaCy pipeline."""
    return spacy.load(model_name)


def detect(model, text: str) -> list[Span]:
    """Return (start, end, label) spans for the targeted entities in `text`."""
    spans: list[Span] = []
    for ent in model(text).ents:
        label = LABEL_MAP.get(ent.label_)
        if label is not None:
            spans.append((ent.start_char, ent.end_char, label))
    return spans
