"""Regex detector for structured PII that NER models do not produce.

Same detector interface as the model-based ones: `load()` and
`detect(model, text) -> list[Span]`. There is no model to load, so `load()` just
returns None and `detect` ignores its `model` argument.

Scope: only entity types with a fixed, recognisable shape. AMOUNT and DATE_TIME are
deliberately left to the NER models, which already handle them well in context.
"""

import re

from ..spans import Span

MODEL_NAME = "regex rules"

# (label, compiled pattern). Overlaps between these and the NER models are resolved
# by the pipeline, not here.
PATTERNS = [
    ("EMAIL_ADDRESS", re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")),
    # Requires an explicit scheme or www., so it will not swallow a bare word. The
    # trailing group stops before a sentence-ending period.
    ("URL", re.compile(r"(?:https?://|www\.)[\w-]+(?:\.[\w-]+)+(?:/\S*)?")),
    # A run of digits and separators long enough to be a phone number, not a year.
    ("PHONE_NUMBER", re.compile(r"\+?\d[\d\s().-]{7,}\d")),
    ("IBAN", re.compile(r"\b[A-Z]{2}\d{2}(?:\s?[A-Z0-9]{2,4}){2,7}\b")),
    # Belgian rijksregisternummer (82.05.30-025.56) or a US-style SSN.
    ("SSN", re.compile(r"\b\d{2}\.\d{2}\.\d{2}-\d{3}\.\d{2}\b|\b\d{3}-\d{2}-\d{4}\b")),
]


def load(model_name: str = MODEL_NAME):
    """Nothing to load: the patterns are compiled at import time."""
    return None


def detect(model, text: str) -> list[Span]:
    """Return (start, end, label) spans for every pattern match in `text`."""
    spans: list[Span] = []
    for label, pattern in PATTERNS:
        for match in pattern.finditer(text):
            spans.append((match.start(), match.end(), label))
    return spans
