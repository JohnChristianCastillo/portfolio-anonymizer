"""Replacing entity spans with placeholders."""

from anonymizer.spans import anonymize_spans


def test_no_spans_leaves_text_untouched():
    assert anonymize_spans("nothing to hide here", []) == "nothing to hide here"


def test_single_span():
    text = "Maria Lopez signed it"
    assert anonymize_spans(text, [(0, 11, "PERSON")]) == "<PERSON> signed it"


def test_span_at_the_end_of_the_text():
    text = "signed by Maria Lopez"
    assert anonymize_spans(text, [(10, 21, "PERSON")]) == "signed by <PERSON>"


def test_several_spans_when_placeholders_are_shorter_than_the_entities():
    # "Maria Lopez" (11) -> "<PERSON>" (8) shortens the string, so a later span's
    # offsets would be stale if replacement ran left to right.
    text = "Maria Lopez likes Ghent"
    spans = [(0, 11, "PERSON"), (18, 23, "LOCATION")]
    assert anonymize_spans(text, spans) == "<PERSON> likes <LOCATION>"


def test_several_spans_when_placeholders_are_longer_than_the_entities():
    # The opposite shift: every placeholder is longer than what it replaces.
    text = "Al lives in NY"
    spans = [(0, 2, "PERSON"), (12, 14, "LOCATION")]
    assert anonymize_spans(text, spans) == "<PERSON> lives in <LOCATION>"


def test_spans_may_arrive_in_any_order():
    text = "Maria Lopez likes Ghent"
    in_order = [(0, 11, "PERSON"), (18, 23, "LOCATION")]
    reversed_order = list(reversed(in_order))
    assert anonymize_spans(text, reversed_order) == anonymize_spans(text, in_order)


def test_adjacent_spans_do_not_lose_the_text_between_them():
    text = "Maria Lopez, Ghent"
    spans = [(0, 11, "PERSON"), (13, 18, "LOCATION")]
    assert anonymize_spans(text, spans) == "<PERSON>, <LOCATION>"


def test_the_whole_text_can_be_one_span():
    assert anonymize_spans("Maria Lopez", [(0, 11, "PERSON")]) == "<PERSON>"
