"""Detect and anonymize sensitive entities (PII) in free text.

The public surface is small: a detector produces spans, the pipeline merges spans
from several detectors, and `anonymize_spans` replaces them with placeholders.
"""

from .pipeline import detect_all
from .spans import Span, anonymize_spans

__all__ = ["Span", "anonymize_spans", "detect_all"]
