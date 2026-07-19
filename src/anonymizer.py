"""Shared anonymization: replace detected entity spans with <LABEL> placeholders.

This is model-agnostic. Every detector returns spans in the same shape, so this one
function anonymizes the output of any model.
"""

# A detected entity: (start_char, end_char, label) with label in the 12-label scheme.
Span = tuple[int, int, str]


def anonymize_spans(text: str, spans: list[Span]) -> str:
    """Replace each span with its <LABEL> placeholder.

    Spans are replaced right-to-left (highest start offset first) so each
    replacement does not shift the offsets of spans still to be replaced.
    """
    for start, end, label in sorted(spans, reverse=True):
        text = text[:start] + f"<{label}>" + text[end:]
    return text
