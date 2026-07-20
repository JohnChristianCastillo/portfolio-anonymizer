"""Shared plumbing for the HuggingFace token-classification detectors.

Each detector module supplies its own model name and label mapping; everything else
about running a transformer is the same, so it lives here.
"""

from transformers import pipeline
from transformers.utils import logging as hf_logging

from ..spans import Span

# Keep output clean: no info banners or weight-loading progress bars.
hf_logging.set_verbosity_error()
hf_logging.disable_progress_bar()


def device_index() -> int:
    """Which device to run on: 0 = first GPU, -1 = CPU.

    Reports CPU whenever the installed torch build has no CUDA support, regardless
    of the hardware present. The default install pins the CPU-only wheel.
    """
    try:
        import torch
    except ImportError:
        return -1
    return 0 if torch.cuda.is_available() else -1


def build(model_name: str):
    """Load a token-classification pipeline for `model_name`.

    A transformer splits words into sub-word tokens, so the aggregation strategy
    decides how those are recombined. 'average' aligns entities to whole words and
    averages the sub-word scores. The 'simple' strategy can return a span covering
    only part of a word, which then replaces mid-word and corrupts the text
    ("Email" becoming "<ORG>ail").
    """
    return pipeline(
        "ner",
        model=model_name,
        aggregation_strategy="average",
        device=device_index(),
    )


def detect_with(model, text: str, label_map: dict[str, str]) -> list[Span]:
    """Return spans for entities whose native label appears in `label_map`."""
    spans: list[Span] = []
    for entity in model(text):
        label = label_map.get(entity["entity_group"])
        if label is not None:
            spans.append((int(entity["start"]), int(entity["end"]), label))
    return spans
