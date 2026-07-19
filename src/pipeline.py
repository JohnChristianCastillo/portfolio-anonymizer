"""Combine several detectors into one list of non-overlapping spans.

Two detectors can claim overlapping characters: a regex EMAIL_ADDRESS may cover a
whole address while a model tags part of it as an ORG. Replacing overlapping spans
would corrupt the text, so conflicts are resolved before any replacement happens.

Resolution order:
  1. Detector priority, earliest first. Regex is passed before the models, since
     fixed-shape data is matched more reliably by a rule than inferred from context.
  2. Longer span, as the more complete entity.
  3. First occurrence, for deterministic output.
Any span overlapping an already-accepted span is dropped.
"""

from anonymizer import Span


def _overlaps(start: int, end: int, accepted: list[Span]) -> bool:
    """True if [start, end) intersects any already-accepted span."""
    for other_start, other_end, _ in accepted:
        if start < other_end and other_start < end:
            return True
    return False


def detect_all(detectors_with_models, text: str) -> list[Span]:
    """Run every detector over `text` and merge the spans they find.

    `detectors_with_models` is a list of (detector_module, loaded_model) in priority
    order, highest priority first.
    """
    # Rank every candidate span so the winners sort to the front. Priority ascends
    # (0 is best) and length is negated so longer spans come first.
    ranked = []
    for priority, (detector, model) in enumerate(detectors_with_models):
        for start, end, label in detector.detect(model, text):
            ranked.append((priority, -(end - start), start, end, label))
    ranked.sort()

    # Greedily keep the best-ranked spans, skipping anything that collides.
    accepted: list[Span] = []
    for _, _, start, end, label in ranked:
        if _overlaps(start, end, accepted):
            continue
        accepted.append((start, end, label))
    return accepted
