"""HuggingFace transformer detector (dslim/bert-base-NER).

Same detector interface as the spaCy one: `detect(model, text) -> list[Span]`.
"""

from huggingface_hub.utils import logging as hub_logging
from transformers import pipeline
from transformers.utils import logging as hf_logging

from anonymizer import Span

# Keep output clean: no info banners, hub notices, or weight-loading progress bars.
hf_logging.set_verbosity_error()
hf_logging.disable_progress_bar()
hub_logging.set_verbosity_error()

MODEL_NAME = "dslim/bert-base-NER"

# Map CoNLL-2003 labels to the target scheme. MISC is too vague, so it is ignored.
# This model has no date/money/etc. labels, so those entities are simply not found.
LABEL_MAP = {
    "PER": "PERSON",
    "ORG": "ORG",
    "LOC": "LOCATION",
}


def load(model_name: str = MODEL_NAME):
    """Load the HuggingFace NER pipeline.

    aggregation_strategy='simple' groups sub-word tokens into whole entities and
    gives each one a character start/end offset.
    """
    return pipeline("ner", model=model_name, aggregation_strategy="simple")


def detect(model, text: str) -> list[Span]:
    """Return (start, end, label) spans for the targeted entities in `text`."""
    spans: list[Span] = []
    for ent in model(text):
        label = LABEL_MAP.get(ent["entity_group"])
        if label is not None:
            spans.append((int(ent["start"]), int(ent["end"]), label))
    return spans
