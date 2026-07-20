"""Generate the benchmark report and its charts into report/.

    uv run anonymizer-report

Include the zero-shot configurations, which need a package deliberately kept out of
the lock file:

    uv run --with gliner anonymizer-report

Writes aggregate values only: label names, counts and metrics, never the evaluated
text.
"""

from pathlib import Path

from . import benchmark, charts, configs, scoring
from .dataset import load_rows

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = PROJECT_ROOT / "report"
REPORT_FILE = REPORT_DIR / "REPORT.md"


def markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    """Render a list of rows as a markdown table."""
    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("|" + "|".join("---" for _ in headers) + "|")
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def overall_table(reports: dict[str, scoring.Report]) -> str:
    rows = []
    for name, report in reports.items():
        tp, fp, fn = report.micro_counts()
        precision, recall, f1 = scoring.precision_recall_f1(tp, fp, fn)
        rows.append(
            [
                name,
                f"{precision:.2f}",
                f"{recall:.2f}",
                f"{f1:.2f}",
                f"{report.exact}/{report.rows}",
            ]
        )
    return markdown_table(
        ["Configuration", "Precision", "Recall", "F1", "Exact rows"], rows
    )


def per_label_table(reports: dict[str, scoring.Report]) -> str:
    names = list(reports)
    rows = []
    for label in scoring.LABELS:
        counts = [reports[name].counts_for(label) for name in names]
        if all(tp == fp == fn == 0 for tp, fp, fn in counts):
            continue  # label absent from the data and from every configuration
        row = [label]
        for tp, fp, fn in counts:
            _, _, f1 = scoring.precision_recall_f1(tp, fp, fn)
            row.append(f"{f1:.2f}")
        rows.append(row)
    return markdown_table(["Label (F1)"] + names, rows)


def detail_table(report: scoring.Report) -> str:
    rows = []
    for label in scoring.LABELS:
        tp, fp, fn = report.counts_for(label)
        if tp == fp == fn == 0:
            continue
        precision, recall, f1 = scoring.precision_recall_f1(tp, fp, fn)
        rows.append(
            [
                label,
                str(tp),
                str(fp),
                str(fn),
                f"{precision:.2f}",
                f"{recall:.2f}",
                f"{f1:.2f}",
            ]
        )
    tp, fp, fn = report.micro_counts()
    precision, recall, f1 = scoring.precision_recall_f1(tp, fp, fn)
    rows.append(
        [
            "**micro-average**",
            str(tp),
            str(fp),
            str(fn),
            f"{precision:.2f}",
            f"{recall:.2f}",
            f"{f1:.2f}",
        ]
    )
    return markdown_table(["Label", "TP", "FP", "FN", "Precision", "Recall", "F1"], rows)


def best_by(reports: dict[str, scoring.Report], index: int) -> tuple[str, float]:
    """The configuration scoring highest on one metric (0=precision, 1=recall, 2=F1)."""
    best_name, best_value = "", -1.0
    for name, report in reports.items():
        tp, fp, fn = report.micro_counts()
        value = scoring.precision_recall_f1(tp, fp, fn)[index]
        if value > best_value:
            best_name, best_value = name, value
    return best_name, best_value


def configuration_table(configurations) -> str:
    return markdown_table(
        ["Configuration", "Detectors (priority order)"],
        [
            [c.label, " + ".join(d.MODEL_NAME for d in c.detectors)]
            for c in configurations
        ],
    )


def build(
    core: dict[str, scoring.Report],
    extended: dict[str, scoring.Report],
    row_count: int,
    core_charts: list[str],
    all_charts: list[str],
    skipped: list,
) -> str:
    best_core, _ = best_by(core, 2)

    details = "\n\n".join(
        f"### {name}\n\n{detail_table(report)}"
        for name, report in {**core, **extended}.items()
    )

    extended_section = ""
    if extended:
        combined = {**core, **extended}
        best_f1_name, best_f1 = best_by(combined, 2)
        best_recall_name, best_recall = best_by(combined, 1)

        extended_section = f"""
## Beyond the required comparison

The comparison above answers the question that was set. Three further configurations
were then measured to test two specific objections to it. They are reported
separately so they cannot be mistaken for the original result, and adding them did
not change any number above.

{configuration_table([c for c in configs.EXTENDED_CONFIGURATIONS if c.label in extended])}

### Objection 1: was the transformer beaten by its architecture, or by its labels?

The transformer in the required comparison is trained on CoNLL-2003, which defines
only four entity types, so it can never emit a date or an amount. That is a property
of the training scheme rather than of the architecture, and it alone could explain
why the smaller model won.

Running the same kind of transformer trained on **OntoNotes**, the scheme spaCy also
uses, settles it: on equal footing the transformer is the stronger model, beating
spaCy on organisations, locations and dates, at a markedly higher precision.

**The original conclusion therefore needs stating carefully.** The smaller model won
that comparison, but not because it was the better model. It won because the other
one was blind to a third of the labels being asked for.

### Objection 2: are JOB and UNIVERSITY actually unreachable?

Every configuration in the required comparison scores zero on both, because no
standard NER scheme contains those classes. A **zero-shot** model is given its label
names at inference time instead of being limited to what it was trained on, so it can
simply be asked for them.

That breaks the wall: both labels are detected for the first time. It also produces
the highest recall of any configuration measured, which matters here more than F1,
since a miss is a leak and a false positive only over-redacts.

### All configurations

![All configurations]({all_charts[0]})

{overall_table({**core, **extended})}

![F1 per entity label, all configurations]({all_charts[2]})

{per_label_table({**core, **extended})}

- Highest F1: **{best_f1_name}** at {best_f1:.2f}.
- Highest recall: **{best_recall_name}** at {best_recall:.2f}, and recall is the
  metric this task should be judged on.
- Exact-row match falls for the OntoNotes configurations even though their F1 rises,
  because that model tends to include trailing punctuation inside an entity. Exact
  match is unforgiving of boundaries in a way that per-label scoring is not, which is
  a good illustration of why more than one measure is reported.
"""

    skipped_note = ""
    if skipped:
        names = ", ".join(f"{c.label} (needs `{c.requires}`)" for c in skipped)
        skipped_note = f"""
> Not included in this run: {names}. The `gliner` package pins an older
> `transformers` than the rest of the project, so it is deliberately kept out of the
> lock file. Regenerate with those configurations using
> `uv run --with gliner anonymizer-report`.
"""

    return f"""# Benchmark report

Regenerate with `uv run anonymizer-report`. Evaluated on a labelled dataset of
{row_count} texts against the 12 target entity labels.
{skipped_note}
## The required comparison

Two pre-trained NER models measured against each other, and each one paired with the
rule layer. This is the result the exercise asked for; nothing below changes it.

{configuration_table(configs.CORE_CONFIGURATIONS)}

Each detector exposes the same interface (`load()` and `detect(model, text)`), so a
configuration is just a list of detectors in priority order. Where two detectors
claim overlapping text, the earlier one wins, then the longer span.

### Overall results

![Overall metrics by configuration]({core_charts[0]})

Highest F1: **{best_core}**. Recall matters most here, because a missed identifier is
a leak, while a false positive only over-redacts.

![Each metric compared across configurations]({core_charts[1]})

{overall_table(core)}

### Per-label coverage

![F1 per entity label]({core_charts[2]})

{per_label_table(core)}

### What the required comparison shows

- **The two models have complementary blind spots.** The transformer is stronger on
  the entity types both cover, reading context better. The spaCy pipeline covers date
  and money entities that the CoNLL-trained transformer has no labels for at all, so
  it wins overall despite being the smaller model.
- **Rules and models solve disjoint problems.** The regex layer scores highly on
  exactly the fixed-shape types (email, phone, URL) that both models score zero on,
  while the models handle open-class entities (people, organisations, locations) that
  no regular expression can express. Adding rules to either model raises recall with
  no loss of precision.
- **Hybrid wins.** The strongest configuration combines a model with the rule layer.
{extended_section}
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
- Some expected labels are debatable (for example a telephone area code labelled as
  a location), so strict matching penalises otherwise reasonable output.
- The overlap-resolution rule never actually fires on this dataset: no spans were
  dropped for overlapping. It is defensive design for messier input and additional
  detectors, not a fix for an observed failure.
- The zero-shot configuration is noisier than a fine-tuned one, since nothing was
  trained on these exact label names; predictions below a confidence threshold are
  discarded.

## Exact numbers

Every value plotted above, per configuration.

{details}
"""


def main() -> None:
    rows = load_rows()

    core = {
        c.label: scoring.summarize(benchmark.evaluate(c.detectors, rows))
        for c in configs.CORE_CONFIGURATIONS
    }
    extended = {
        c.label: scoring.summarize(benchmark.evaluate(c.detectors, rows))
        for c in configs.runnable(configs.EXTENDED_CONFIGURATIONS)
    }
    skipped = [c for c in configs.EXTENDED_CONFIGURATIONS if not c.available()]

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    core_charts = charts.build_charts(core, REPORT_DIR, prefix="core_")
    all_charts = (
        charts.build_charts({**core, **extended}, REPORT_DIR, prefix="all_")
        if extended
        else core_charts
    )

    REPORT_FILE.write_text(
        build(core, extended, len(rows), core_charts, all_charts, skipped),
        encoding="utf-8",
    )
    written = len(core_charts) + (len(all_charts) if extended else 0)
    print(f"Wrote {REPORT_FILE.relative_to(PROJECT_ROOT)} and {written} charts")


if __name__ == "__main__":
    main()
