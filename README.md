# portfolio-anonymizer

Detects and anonymizes sensitive entities (PII) in free text using pre-trained
named-entity-recognition models combined with rule-based matching, and benchmarks
the configurations against a labelled dataset.

Anonymizing means replacing each detected entity with its `<LABEL>` placeholder:

```
Maria Lopez works for Contoso Ltd.  ->  <PERSON> works for <ORG>.
```

## Entity labels

PERSON, ORG, JOB, EMAIL_ADDRESS, LOCATION, AMOUNT, DATE_TIME, UNIVERSITY,
PHONE_NUMBER, URL, IBAN, SSN

## How it works

A **detector** is anything exposing `load()` and
`detect(model, text) -> list of (start, end, label)`. Because every detector
returns the same shape, the stages after it never depend on which model produced a
span, and adding a model is a one-line change.

```text
   input text
       |
       v
+--------------------------------------------+
| Detectors  (one shared interface)          |
|   regex_detector    priority 0  (rules)    |
|   spacy_detector    priority 1  (model)    |
|   hf_detector       priority 1  (model)    |
+--------------------------------------------+
       |  spans: (start, end, label)
       v
+--------------------------------------------+
| pipeline.detect_all                        |
|   rank by priority, then longest span      |
|   drop any span overlapping a kept one     |
+--------------------------------------------+
       |  non-overlapping spans
       v
+--------------------------------------------+
| anonymizer.anonymize_spans                 |
|   replace each span right-to-left          |
+--------------------------------------------+
       |  anonymized text
       v
+--------------------------------------------+
| scoring                                    |
|   result vs expected                       |
|   precision / recall / F1, micro-average   |
+--------------------------------------------+
```

Spans are replaced right-to-left so that earlier replacements never shift the
offsets of spans still to be replaced.

## Models

Public, pre-trained models only; nothing is trained here and no weights are
committed. Each is declared as a dependency and fetched on first use.

| Detector | What it is | Labels it contributes |
|---|---|---|
| `spacy_detector` | spaCy `en_core_web_sm` | PERSON, ORG, LOCATION, DATE_TIME, AMOUNT |
| `hf_detector` | HuggingFace `dslim/bert-base-NER` (BERT transformer) | PERSON, ORG, LOCATION |
| `regex_detector` | Rule patterns | EMAIL_ADDRESS, URL, PHONE_NUMBER, IBAN, SSN |

Rules handle entities with a fixed shape; models handle open-class entities whose
identity depends on context. The two cover disjoint labels, which is why the
strongest configuration combines them.

## Results

Full write-up with charts: **[report/REPORT.md](report/REPORT.md)**

![Overall metrics by configuration](report/overall_metrics.png)

Adding the rule layer to either model raises recall with no loss of precision.
JOB and UNIVERSITY are not reached by any configuration; see the report for why.

## Setup

Requires [uv](https://docs.astral.sh/uv/).

```bash
scripts/01_setup.sh     # or scripts\01_setup.ps1 on Windows
```

That creates the environment from `uv.lock`, so it is reproducible exactly.

## Running

```bash
scripts/02_run.sh       # or scripts\02_run.ps1 - runs the benchmark
```

Regenerate the report and its charts:

```bash
uv run python src/make_report.py
```

## Dataset format

Datasets are not committed. Place a semicolon-separated CSV at
`data/benchmark.csv` with two columns:

- `text` - the original text
- `label` - the same text with every sensitive entity replaced by its `<LABEL>`
  placeholder

```
text;label
Maria Lopez works for Contoso Ltd.;<PERSON> works for <ORG>.
```

## Project layout

```
src/
  dataset.py          load the labelled rows
  regex_detector.py   rule-based detector
  spacy_detector.py   spaCy detector
  hf_detector.py      HuggingFace transformer detector
  pipeline.py         merge detectors, resolve overlapping spans
  anonymizer.py       replace spans with placeholders
  scoring.py          precision / recall / F1 and model comparison
  benchmark.py        run every configuration
  make_report.py      generate report/REPORT.md
  make_charts.py      render the report charts
scripts/              numbered setup and run scripts (.sh and .ps1)
report/               generated benchmark report and charts
```

## Limitations

- The evaluation set is small, so per-label scores move a lot per entity.
- JOB and UNIVERSITY have no class in standard NER schemes and no fixed shape for
  a rule, so they need a gazetteer, hand-written patterns, or a zero-shot model.
- Phone and IBAN patterns are pragmatic heuristics, not full format specifications.
