"""HuggingFace transformer detector (dslim/bert-base-NER).

Same detector interface as the spaCy one: `detect(model, text) -> list[Span]`.
"""

from huggingface_hub.utils import logging as hub_logging
from transformers import pipeline
from transformers.utils import logging as hf_logging

from ..spans import Span

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


def device_index() -> int:
    """Which device the transformer should run on: 0 = first GPU, -1 = CPU.

    Note this reports CPU whenever the installed torch build has no CUDA support,
    regardless of the hardware present. The default install pins the CPU-only wheel
    (see pyproject), so a machine with a GPU needs a CUDA build of torch before this
    can return a GPU. For short texts the difference is marginal either way.
    """
    try:
        import torch
    except ImportError:
        return -1
    return 0 if torch.cuda.is_available() else -1


def load(model_name: str = MODEL_NAME):
    """Load the HuggingFace NER pipeline, on a GPU when one is usable.

    A transformer splits words into sub-word tokens, so the aggregation strategy
    decides how those are recombined into entities. 'average' is used because it
    aligns entities to whole words and averages the sub-word scores. The 'simple'
    strategy can return a span covering only part of a word, which then replaces
    mid-word and corrupts the text ("Email" becoming "<ORG>ail"), and it also lets a
    single high-scoring fragment create an entity that word-level averaging rejects.
    """
    return pipeline(
        "ner",
        model=model_name,
        aggregation_strategy="average",
        device=device_index(),
    )


def detect(model, text: str) -> list[Span]:
    """Return (start, end, label) spans for the targeted entities in `text`."""
    spans: list[Span] = []
    for ent in model(text):
        label = LABEL_MAP.get(ent["entity_group"])
        if label is not None:
            spans.append((int(ent["start"]), int(ent["end"]), label))
    return spans
