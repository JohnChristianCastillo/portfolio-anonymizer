"""Reusable scorer: compare a RESULT string against the EXPECTED string.

Both strings are anonymized text in which entities are <LABEL> placeholders. The
scorer reports, per label, precision / recall / F1, plus a micro-average and the
exact-row-match count. It has no model-specific code, so every model reuses it.

How it works (v1, standard library only):
  1. split RESULT and EXPECTED into whitespace tokens,
  2. align the two token lists with difflib,
  3. count, per label:
       - true positive  : an EXPECTED <L> that RESULT also produced,
       - false negative : an EXPECTED <L> that RESULT missed (a leak),
       - false positive : an <L> RESULT produced where EXPECTED had none.
Matching inside a mismatched region is done per label, so small boundary
differences (for example "<ORG>" vs "<ORG>.") still count as a hit.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from difflib import SequenceMatcher

# The 12 target labels, used to order the report.
LABELS = [
    "PERSON", "ORG", "JOB", "EMAIL_ADDRESS", "LOCATION", "AMOUNT",
    "DATE_TIME", "UNIVERSITY", "PHONE_NUMBER", "URL", "IBAN", "SSN",
]

_PLACEHOLDER = re.compile(r"<([A-Z_]+)>")


def _label_of(token: str) -> str | None:
    """Return the label inside a token like '<ORG>.' -> 'ORG', else None."""
    match = _PLACEHOLDER.search(token)
    return match.group(1) if match else None


def _labels_in(tokens: list[str]) -> Counter:
    """Count placeholder labels in a run of tokens."""
    counts = Counter()
    for token in tokens:
        label = _label_of(token)
        if label is not None:
            counts[label] += 1
    return counts


@dataclass
class Tally:
    """Running true/false positive/negative counts per label."""

    tp: Counter = field(default_factory=Counter)
    fp: Counter = field(default_factory=Counter)
    fn: Counter = field(default_factory=Counter)

    def add(self, other: "Tally") -> None:
        self.tp.update(other.tp)
        self.fp.update(other.fp)
        self.fn.update(other.fn)


def tally_row(result: str, expected: str) -> Tally:
    """Tally true/false positives/negatives for one RESULT vs EXPECTED pair."""
    exp_tokens = expected.split()
    res_tokens = result.split()
    tally = Tally()

    matcher = SequenceMatcher(a=exp_tokens, b=res_tokens, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        exp_labels = _labels_in(exp_tokens[i1:i2])
        res_labels = _labels_in(res_tokens[j1:j2])

        if tag == "equal":
            # Tokens are identical, so any placeholder here is a correct match.
            tally.tp.update(exp_labels)
        else:
            # Mismatched region: match per label; leftovers are misses / extras.
            for label in set(exp_labels) | set(res_labels):
                matched = min(exp_labels[label], res_labels[label])
                tally.tp[label] += matched
                tally.fn[label] += exp_labels[label] - matched
                tally.fp[label] += res_labels[label] - matched
    return tally


def precision_recall_f1(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    """Turn hit / false-alarm / miss counts into the three metrics.

    tp = true positives (hits), fp = false positives (false alarms),
    fn = false negatives (misses).
      precision = hits / everything flagged   (how trustworthy the flags are)
      recall    = hits / everything expected  (how much real PII was caught)
      f1        = balanced combination of precision and recall
    """
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return precision, recall, f1


def score(pairs: list[tuple[str, str]]) -> None:
    """Score a list of (result, expected) pairs and print the report.

    The table is aligned with f-string format specs. Worked example of one row,
    for label='PERSON', tp=7, fp=0, fn=0, p=1.0, r=1.0, f=1.0:

        f"{label:<14}{tp:>4}{fp:>4}{fn:>4}{p:>8.2f}{r:>8.2f}{f:>8.2f}"

    produces (dots shown here as spaces):

        PERSON........   7   0   0    1.00    1.00    1.00
        |<-- 14 -->||-4-||-4-||-4-||-- 8 --||-- 8 --||-- 8 -|

    So {label:<14} left-aligns 'PERSON' padded to 14 wide, {tp:>4} right-aligns 7
    to 4 wide, and {p:>8.2f} writes 1.0 as '    1.00' (8 wide, 2 decimals).
    """
    total = Tally()
    exact = 0
    for result, expected in pairs:
        if result.strip() == expected.strip():
            exact += 1
        total.add(tally_row(result, expected))

    # Column widths match the worked example in this function's docstring.
    header = f"{'LABEL':<14}{'TP':>4}{'FP':>4}{'FN':>4}{'PREC':>8}{'REC':>8}{'F1':>8}"
    print(header)
    print("-" * len(header))

    # Running totals across every label, used for the overall score below.
    micro_tp = micro_fp = micro_fn = 0
    for label in LABELS:
        tp, fp, fn = total.tp[label], total.fp[label], total.fn[label]
        if tp == fp == fn == 0:
            continue  # label not present at all - skip
        micro_tp += tp
        micro_fp += fp
        micro_fn += fn
        p, r, f = precision_recall_f1(tp, fp, fn)
        print(f"{label:<14}{tp:>4}{fp:>4}{fn:>4}{p:>8.2f}{r:>8.2f}{f:>8.2f}")

    print("-" * len(header))
    # "Micro-average": pool every label's counts into one total and score that,
    # so each entity counts equally (labels with more entities weigh more).
    p, r, f = precision_recall_f1(micro_tp, micro_fp, micro_fn)
    print(f"{'MICRO-AVG':<14}{micro_tp:>4}{micro_fp:>4}{micro_fn:>4}{p:>8.2f}{r:>8.2f}{f:>8.2f}")
    print(f"\nExact row matches: {exact}/{len(pairs)}")


if __name__ == "__main__":
    # Self-check on tiny hand-made examples (no model needed).
    demo = [
        ("<PERSON> likes <LOCATION>", "<PERSON> likes <LOCATION>"),  # perfect
        ("John likes <LOCATION>", "<PERSON> likes <LOCATION>"),      # missed PERSON
        ("<PERSON> likes <ORG>", "<PERSON> likes <LOCATION>"),       # wrong label
    ]
    score(demo)
