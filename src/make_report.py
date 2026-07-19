"""Generate the benchmark report and its charts into report/.

    uv run python src/make_report.py

Writes aggregate values only: label names, counts and metrics, never the evaluated
text.
"""

from pathlib import Path

import benchmark
import make_charts
import scoring
from dataset import load_rows

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORT_DIR = PROJECT_ROOT / "report"
REPORT_FILE = REPORT_DIR / "REPORT.md"


def markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    """Render a list of rows as a markdown table."""
    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("|" + "|".join("---" for _ in headers) + "|")
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def detail_table(report: scoring.Report) -> str:
    rows = []
    for label in scoring.LABELS:
        tp, fp, fn = report.counts_for(label)
        if tp == fp == fn == 0:
            continue
        precision, recall, f1 = scoring.precision_recall_f1(tp, fp, fn)
        rows.append(
            [label, str(tp), str(fp), str(fn), f"{precision:.2f}", f"{recall:.2f}", f"{f1:.2f}"]
        )
    tp, fp, fn = report.micro_counts()
    precision, recall, f1 = scoring.precision_recall_f1(tp, fp, fn)
    rows.append(
        ["**micro-average**", str(tp), str(fp), str(fn), f"{precision:.2f}", f"{recall:.2f}", f"{f1:.2f}"]
    )
    return markdown_table(["Label", "TP", "FP", "FN", "Precision", "Recall", "F1"], rows)


def build(reports: dict[str, scoring.Report], row_count: int, charts: list[str]) -> str:
    configurations = markdown_table(
        ["Configuration", "Detectors (priority order)"],
        [
            [name, " + ".join(d.MODEL_NAME for d in detectors)]
            for name, detectors in benchmark.SYSTEMS
        ],
    )

    # The configuration with the highest micro-average F1.
    best = ""
    best_f1 = -1.0
    for name, report in reports.items():
        tp, fp, fn = report.micro_counts()
        _, _, f1 = scoring.precision_recall_f1(tp, fp, fn)
        if f1 > best_f1:
            best_f1 = f1
            best = name

    details = "\n\n".join(
        f"### {name}\n\n{detail_table(report)}" for name, report in reports.items()
    )

    return f"""# Benchmark report

Regenerate with `uv run python src/make_report.py`. Evaluated on a labelled dataset
of {row_count} texts against the 12 target entity labels.

## Configurations compared

{configurations}

Each detector exposes the same interface (`load()` and `detect(model, text)`), so a
configuration is just a list of detectors in priority order. Where two detectors
claim overlapping text, the earlier one wins, then the longer span.

## Overall results

![Overall metrics by configuration]({charts[0]})

Highest F1: **{best}**. Recall matters most here, because a missed identifier is a
leak, while a false positive only over-redacts.

![Each metric compared across configurations]({charts[1]})

Read down a single panel to compare one attribute across configurations: precision
stays flat while recall moves, which is where the differences actually live.

## Per-label coverage

![F1 per entity label]({charts[2]})

The blank column blocks are the story: each configuration is blind to a different
set of labels.

## What the results show

- **The two models have complementary blind spots.** The transformer is stronger on
  the entity types both cover, reading context better. The spaCy pipeline covers
  date and money entities that the CoNLL-trained transformer has no labels for at
  all, so it wins overall despite being the smaller model.
- **The best model depends on label coverage, not just architecture.** A more modern
  architecture does not help for entity types absent from its training scheme.
- **Rules and models solve disjoint problems.** The regex layer scores highly on
  exactly the fixed-shape types (email, phone, URL) that both models score zero on,
  while the models handle open-class entities (people, organisations, locations)
  that no regular expression can express. Adding rules to either model raises recall
  with no loss of precision.
- **Hybrid wins.** The strongest configuration combines a model with the rule layer.

## How the scoring works

The anonymized RESULT is compared against the EXPECTED answer by aligning the two
token sequences (Python's `difflib`). Per label:

- **TP**: an expected `<LABEL>` the configuration also produced.
- **FP**: a `<LABEL>` produced where none was expected (over-anonymizing).
- **FN**: an expected `<LABEL>` that was missed (a leak).

From those, precision = TP/(TP+FP), recall = TP/(TP+FN), and F1 is their harmonic
mean. The micro-average pools every label's counts into one total.

Counts are aggregated over every occurrence of a label across all texts, not per
text, which is why a per-label score is usually a fraction: a label occurring eight
times with six caught and two missed scores 0.75, not 0 or 1. A label scores exactly
1.00 only when every occurrence was caught with no false positives, which is easiest
for labels that occur once or twice.

"Exact rows" counts texts where the whole anonymized output matched the expected
string character for character, which is a deliberately strict measure.

## Limitations

- The evaluation set is small, so per-label figures move a lot per entity; treat the
  numbers as indicative rather than precise.
- JOB and UNIVERSITY are not produced by any configuration. No standard NER scheme
  has those classes and they have no fixed shape for a rule to match, so they need a
  gazetteer, hand-written patterns, or a zero-shot model.
- Some expected labels are debatable (for example a telephone area code labelled as
  a location), so strict matching penalises otherwise reasonable output.
- The overlap-resolution rule never actually fires on this dataset: no spans were
  dropped for overlapping. It is defensive design for messier input and additional
  detectors, not a fix for an observed failure.

## Exact numbers

Every value plotted above, per configuration.

{details}
"""


def main() -> None:
    rows = load_rows()
    reports = {}
    for name, detectors in benchmark.SYSTEMS:
        reports[name] = scoring.summarize(benchmark.evaluate(detectors, rows))

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    charts = make_charts.build_charts(reports, REPORT_DIR)
    REPORT_FILE.write_text(build(reports, len(rows), charts), encoding="utf-8")
    print(f"Wrote {REPORT_FILE.relative_to(PROJECT_ROOT)} and {len(charts)} charts")


if __name__ == "__main__":
    main()
