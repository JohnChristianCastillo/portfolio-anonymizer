"""Merging several detectors into one set of non-overlapping spans."""

from anonymizer import pipeline


class StubDetector:
    """A detector that always reports the spans it was given.

    The pipeline only needs `detect(model, text)`, so a real model is never loaded
    here and the resolution rules can be tested on their own.
    """

    def __init__(self, *spans):
        self.spans = list(spans)

    def detect(self, model, text):
        return list(self.spans)


def merge(*detectors, text="some text long enough for these offsets"):
    return pipeline.detect_all([(d, None) for d in detectors], text)


def test_no_detectors_finds_nothing():
    assert merge() == []


def test_non_overlapping_spans_from_two_detectors_are_all_kept():
    first = StubDetector((0, 4, "PERSON"))
    second = StubDetector((10, 14, "LOCATION"))
    assert sorted(merge(first, second)) == [(0, 4, "PERSON"), (10, 14, "LOCATION")]


def test_the_earlier_detector_wins_an_overlap():
    # Detectors are passed in priority order, so the rule layer is placed first.
    rules = StubDetector((0, 10, "EMAIL_ADDRESS"))
    model = StubDetector((3, 8, "ORG"))
    assert merge(rules, model) == [(0, 10, "EMAIL_ADDRESS")]


def test_priority_beats_length():
    # The lower-priority span is longer, but priority is checked first.
    rules = StubDetector((0, 5, "SSN"))
    model = StubDetector((0, 20, "ORG"))
    assert merge(rules, model) == [(0, 5, "SSN")]


def test_within_one_detector_the_longer_span_wins():
    detector = StubDetector((0, 5, "PERSON"), (0, 12, "ORG"))
    assert merge(detector) == [(0, 12, "ORG")]


def test_partial_overlap_is_still_a_conflict():
    first = StubDetector((0, 10, "PERSON"))
    second = StubDetector((8, 16, "LOCATION"))
    assert merge(first, second) == [(0, 10, "PERSON")]


def test_touching_spans_are_not_an_overlap():
    # One span ending exactly where the next begins is fine: [0,5) and [5,9).
    first = StubDetector((0, 5, "PERSON"))
    second = StubDetector((5, 9, "LOCATION"))
    assert sorted(merge(first, second)) == [(0, 5, "PERSON"), (5, 9, "LOCATION")]


def test_the_result_never_contains_overlapping_spans():
    noisy = StubDetector((0, 10, "PERSON"), (5, 15, "ORG"), (12, 20, "LOCATION"))
    spans = sorted(merge(noisy))
    for (_, first_end, _), (second_start, _, _) in zip(spans, spans[1:], strict=False):
        assert first_end <= second_start
