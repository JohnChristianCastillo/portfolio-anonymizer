"""Scoring a result against the expected answer."""

import pytest

from anonymizer import scoring


def counts(result: str, expected: str) -> dict[str, tuple[int, int, int]]:
    """Per-label (tp, fp, fn) for one pair, limited to labels that were involved."""
    tally = scoring.tally_row(result, expected)
    labels = set(tally.tp) | set(tally.fp) | set(tally.fn)
    return {
        label: (tally.tp[label], tally.fp[label], tally.fn[label]) for label in labels
    }


# --- the three counts -------------------------------------------------------


def test_an_exact_match_is_a_true_positive():
    assert counts("<PERSON> called", "<PERSON> called") == {"PERSON": (1, 0, 0)}


def test_a_missed_entity_is_a_false_negative():
    assert counts("Maria called", "<PERSON> called") == {"PERSON": (0, 0, 1)}


def test_an_invented_entity_is_a_false_positive():
    assert counts("<PERSON> called", "Maria called") == {"PERSON": (0, 1, 0)}


def test_the_wrong_label_is_both_a_miss_and_a_false_alarm():
    assert counts("<ORG> called", "<PERSON> called") == {
        "ORG": (0, 1, 0),
        "PERSON": (0, 0, 1),
    }


def test_identical_text_with_no_entities_scores_nothing():
    assert counts("nothing to see", "nothing to see") == {}


def test_a_boundary_difference_still_counts_as_a_hit():
    # The model included the trailing period in the entity, the answer key did not.
    # That is the same finding, so it should not be punished twice.
    assert counts("works at <ORG> today", "works at <ORG>. today") == {"ORG": (1, 0, 0)}


def test_repeated_labels_are_counted_per_occurrence():
    assert counts("<PERSON> met <PERSON>", "<PERSON> met <PERSON>") == {
        "PERSON": (2, 0, 0)
    }


def test_one_of_two_occurrences_missed():
    assert counts("<PERSON> met Sofie", "<PERSON> met <PERSON>") == {"PERSON": (1, 0, 1)}


# --- the metrics ------------------------------------------------------------


def test_precision_recall_f1_on_a_perfect_score():
    assert scoring.precision_recall_f1(5, 0, 0) == (1.0, 1.0, 1.0)


def test_precision_ignores_misses_and_recall_ignores_false_alarms():
    precision, recall, _ = scoring.precision_recall_f1(tp=6, fp=2, fn=2)
    assert precision == pytest.approx(0.75)
    assert recall == pytest.approx(0.75)


def test_f1_is_the_harmonic_mean_so_it_punishes_imbalance():
    # precision 1.00, recall 0.50: the plain average would flatter this at 0.75.
    _, _, f1 = scoring.precision_recall_f1(tp=5, fp=0, fn=5)
    assert f1 == pytest.approx(2 / 3, abs=1e-3)


def test_metrics_are_zero_rather_than_dividing_by_zero():
    assert scoring.precision_recall_f1(0, 0, 0) == (0.0, 0.0, 0.0)


def test_detecting_nothing_scores_zero_even_with_no_false_alarms():
    precision, recall, f1 = scoring.precision_recall_f1(tp=0, fp=0, fn=8)
    assert (precision, recall, f1) == (0.0, 0.0, 0.0)


# --- aggregation ------------------------------------------------------------


def test_summarize_counts_exact_row_matches():
    report = scoring.summarize(
        [
            ("<PERSON> called", "<PERSON> called"),  # exact
            ("Maria called", "<PERSON> called"),  # not exact
        ]
    )
    assert report.exact == 1
    assert report.rows == 2


def test_micro_counts_pool_every_label():
    report = scoring.summarize(
        [
            ("<PERSON> at <ORG>", "<PERSON> at <ORG>"),  # 2 hits
            ("Maria at <ORG>", "<PERSON> at <ORG>"),  # 1 hit, 1 miss
        ]
    )
    assert report.micro_counts() == (3, 0, 1)


def test_counts_for_a_single_label():
    report = scoring.summarize([("Maria at <ORG>", "<PERSON> at <ORG>")])
    assert report.counts_for("ORG") == (1, 0, 0)
    assert report.counts_for("PERSON") == (0, 0, 1)


def test_a_label_that_never_appears_is_all_zeros():
    report = scoring.summarize([("<PERSON> called", "<PERSON> called")])
    assert report.counts_for("IBAN") == (0, 0, 0)
