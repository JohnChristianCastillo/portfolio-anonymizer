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
# Order is precedence: the first pattern to claim a stretch of text keeps it.
# Specific formats come before loose ones, because the phone pattern is deliberately
# permissive (numbers are written many ways) and would otherwise swallow an IBAN or a
# national number, both of which are also digits and separators.
PATTERNS = [
    ("EMAIL_ADDRESS", re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")),
    # Requires an explicit scheme or www., so it will not swallow a bare word. The
    # path may not end on punctuation, so a sentence-ending period stays outside.
    (
        "URL",
        re.compile(r"(?:https?://|www\.)[\w-]+(?:\.[\w-]+)+(?:/[\w\-./%?=&#]*[\w/])?"),
    ),
    ("IBAN", re.compile(r"\b[A-Z]{2}\d{2}(?:\s?[A-Z0-9]{2,4}){2,7}\b")),
    # National identifier numbers. Every country formats these differently, so this
    # covers two shapes rather than pretending to be general: the Belgian
    # rijksregisternummer (82.05.30-025.56) and the US pattern (123-45-6789).
    # Supporting more countries means adding a pattern per format, which is a known
    # limitation for work spanning several European jurisdictions.
    ("SSN", re.compile(r"\b\d{2}\.\d{2}\.\d{2}-\d{3}\.\d{2}\b|\b\d{3}-\d{2}-\d{4}\b")),
    # A run of digits and separators long enough to be a phone number, not a year.
    ("PHONE_NUMBER", re.compile(r"\+?\d[\d\s().-]{7,}\d")),
]


def load(model_name: str = MODEL_NAME):
    """Nothing to load: the patterns are compiled at import time."""
    return None


def _claimed(start: int, end: int, spans: list[Span]) -> bool:
    """True if [start, end) overlaps a span an earlier pattern already took."""
    for other_start, other_end, _ in spans:
        if start < other_end and other_start < end:
            return True
    return False


def detect(model, text: str) -> list[Span]:
    """Return (start, end, label) spans for every pattern match in `text`.

    Patterns are applied in PATTERNS order and a match is skipped when an earlier,
    more specific pattern already claimed that text, so a national number is not
    also reported as a phone number.
    """
    spans: list[Span] = []
    for label, pattern in PATTERNS:
        for match in pattern.finditer(text):
            if _claimed(match.start(), match.end(), spans):
                continue
            spans.append((match.start(), match.end(), label))
    return spans
