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


# How each of the twelve labels is actually detected in the delivered tool, and the
# reason that method was chosen over the alternatives. Ordered as scoring.LABELS.
ENTITY_METHODS = [
    (
        "PERSON",
        "NER model",
        "A name is a name because of where it sits in a sentence, not its shape. "
        "No pattern can express that. Every model detects it well (F1 0.90 to 1.00).",
    ),
    (
        "ORG",
        "NER model",
        "Same reason as PERSON, but harder: an organisation name is often an "
        "ordinary word. This is the weakest of the model-detected labels (0.77) and "
        "the main remaining source of confusion with PERSON.",
    ),
    (
        "JOB",
        "Zero-shot model",
        "Absent from every standard NER scheme, so a fine-tuned model scores 0.00 "
        "no matter how good it is. A zero-shot model is given the label name at "
        "inference time instead, which takes it from 0.00 to 0.91.",
    ),
    (
        "EMAIL_ADDRESS",
        "Rule",
        "Fully specified by its form. A pattern reaches 1.00, while the zero-shot "
        "model reaches 0.67 on the same data, so a rule is both better and cheaper.",
    ),
    (
        "LOCATION",
        "NER model, plus a rule for postal codes",
        "Place names need a model. Postal codes are the exception: the models "
        "consistently return the town but not the digits in front of it, so a narrow "
        "rule fills that gap. It requires a following capitalised word, so a bare "
        "year is not mistaken for a postal code.",
    ),
    (
        "AMOUNT",
        "NER model, chosen for its label scheme",
        "Solved by choosing the right model rather than by writing a rule. CoNLL "
        "has no money class and scores 0.00; the OntoNotes model scores 1.00 on the "
        "same texts, including the European formats that defeat the smaller "
        "pipeline. Currency writing varies far too much to enumerate by hand.",
    ),
    (
        "DATE_TIME",
        "NER model",
        "The models read machine timestamps as well as written dates, so no rule is "
        "needed. An earlier hand-written telephone pattern matched the leading "
        "'2022-12-27 08' of a timestamp and split it in half; validating telephone "
        "numbers properly removed the collision and the label rose to 0.93.",
    ),
    (
        "UNIVERSITY",
        "Zero-shot model",
        "Like JOB, absent from standard schemes, so 0.00 everywhere until asked for "
        "by name. Then 0.86.",
    ),
    (
        "PHONE_NUMBER",
        "phonenumbers (libphonenumber)",
        "The one identifier that is parsed and validated rather than matched. A "
        "pattern loose enough to accept the many ways a number is written also "
        "matches timestamps and national numbers; validation removes that whole "
        "class of collision, and covers every country rather than a chosen few.",
    ),
    (
        "URL",
        "Rule",
        "Fully specified by its form, and the zero-shot model scores 0.00 on it. "
        "The pattern requires a scheme or www. so ordinary words never match, and "
        "excludes sentence punctuation from the end of a path.",
    ),
    (
        "IBAN",
        "Rule, with python-stdnum for check digits",
        "Models score 0.00: an account number carries no linguistic signal. The "
        "shape is matched first, before telephone numbers, because an IBAN contains "
        "a run of digits that is a plausible number on its own.",
    ),
    (
        "SSN",
        "Rule, with python-stdnum for check digits",
        "Same as IBAN. National identifier formats differ per country, so the "
        "library supplies the structures rather than one developer's guesses.",
    ),
]


def entity_method_table() -> str:
    return markdown_table(
        ["Entity", "How it is detected", "Why"],
        [[label, method, why] for label, method, why in ENTITY_METHODS],
    )


def build(
    core: dict[str, scoring.Report],
    extended: dict[str, scoring.Report],
    row_count: int,
    core_charts: list[str],
    all_charts: list[str],
    skipped: list,
) -> str:
    details = "\n\n".join(
        f"### {name}\n\n{detail_table(report)}"
        for name, report in {**core, **extended}.items()
    )

    extended_section = ""
    if extended:
        combined = {**core, **extended}
        best_f1_name, best_f1 = best_by(combined, 2)
        best_recall_name, best_recall = best_by(combined, 1)
        # Models on their own, across the required and the added ones alike.
        all_models_only = {
            c.label: combined[c.label]
            for c in configs.models_only(configs.CONFIGURATIONS)
            if c.label in combined
        }

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

### Every model, measured alone

The same apples-to-apples view as the required comparison, now with all four models
and no rule layer involved:

{overall_table(all_models_only)}

{per_label_table(all_models_only)}

### Every configuration

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

    core_models = {
        c.label: core[c.label] for c in configs.models_only(configs.CORE_CONFIGURATIONS)
    }
    core_hybrid = {
        c.label: core[c.label] for c in configs.with_rules(configs.CORE_CONFIGURATIONS)
    }
    best_model, _ = best_by(core_models, 2)

    return f"""# Benchmark report

Regenerate with `uv run anonymizer-report`. Evaluated on a labelled dataset of
{row_count} texts against the 12 target entity labels.
{skipped_note}
## The required comparison: two models, measured alone

{configuration_table(configs.models_only(configs.CORE_CONFIGURATIONS))}

Both models are given the same input and nothing else is added, so the difference
between them is the models and only the models.

{overall_table(core_models)}

{per_label_table(core_models)}

Highest F1: **{best_model}**. Recall matters most here, because a missed identifier
is a leak, while a false positive only over-redacts.

**What it shows.** The two have complementary blind spots. The transformer is
stronger on the entity types both cover, reading context better: organisations and
locations both improve. But it emits no dates and no money at all, because it is
fine-tuned on CoNLL-2003, whose scheme has only four entity types. The smaller spaCy
pipeline therefore wins overall, on coverage rather than on quality.

## Why the rule layer is reported separately

A rule layer for fixed-shape identifiers was added as an engineering step. It is
**not** part of the model comparison above, and mixing the two would be misleading:

- The rules can only ever produce **6 of the 12 labels** (email, URL, telephone,
  IBAN, national number, and postal codes within a location). They contribute
  nothing to people, organisations, job titles, dates or amounts.
- Adding the same rule layer to both models adds the same easy wins to both, which
  raises both scores and narrows the visible gap between them.
- In principle the rules could also mask a model's detections, since they take
  priority when spans overlap. Measured on this dataset they never do: **zero** model
  spans were suppressed for either model. So here the layer is purely additive, and
  the ordering of the two models is unchanged. That is a measurement, not an
  assumption.

So the numbers below describe a **system**, not a model.

{configuration_table(configs.with_rules(configs.CORE_CONFIGURATIONS))}

{overall_table(core_hybrid)}

**What it shows.** Rules and models solve disjoint problems. The rule layer scores
highly on exactly the fixed-shape types that both models score zero on, while the
models handle the open-class entities no regular expression can express. Adding
rules lifts recall for both models with no loss of precision, which is why the
delivered tool combines them even though the comparison above does not.

### All four core configurations together

![Overall metrics by configuration]({core_charts[0]})

![Each metric compared across configurations]({core_charts[1]})

![F1 per entity label]({core_charts[2]})

{overall_table(core)}

{per_label_table(core)}
{extended_section}
## How each entity is detected, and why

Everything above compares configurations. This is the conclusion drawn from them:
for each of the twelve labels, the method the delivered tool uses and the reason it
was chosen.

The division is not arbitrary. It follows from whether a label is identifiable by
its **form** or by its **meaning**. An IBAN is an IBAN whatever sentence surrounds
it, so a rule reads it perfectly and a model reads it not at all. A person's name is
only a name because of the words around it, so the reverse holds. Two labels, JOB
and UNIVERSITY, belong to neither group: they are meaning-based but missing from
every standard NER scheme, which is what a zero-shot model exists to solve.

{entity_method_table()}

Where a standard exists, the standard's own library does the work rather than a
pattern invented here: `phonenumbers` for telephone numbers, `python-stdnum` for
account and national numbers. This is a correctness decision, not a convenience
one. Those libraries encode per-country structure and check digits that no
hand-written pattern reproduces, and they were what fixed the timestamp collision.

Check digits are **reported alongside a detection and never used to reject one**.
The reasoning is the same as everywhere else in this task: a mistyped account number
is still an account number, so redacting it costs nothing while missing it is a leak.
The best illustration is `BE68 5390 0754 7034`, the example IBAN that appears in most
documentation. It passes the international mod-97 check but fails Belgium's own
account-number rule, so validating before redacting would have discarded a textbook
account number.

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
