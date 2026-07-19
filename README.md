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
|   regex_rules      priority 0  (rules)     |
|   spacy_model      priority 1  (model)     |
|   hf_model         priority 1  (model)     |
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
| spans.anonymize_spans                      |
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
uv run anonymizer-report
```

## Web app

A React front end provides the interactive demo: paste text, pick a detector
configuration, and see the detected entities and the anonymized output side by side.

Local development (two terminals):

```bash
scripts/03_serve.sh              # backend on :8400
cd frontend && npm install && npm run dev   # Vite on :5173, proxies /api to :8400
```

Build for deployment:

```bash
cd frontend && npm run build     # -> frontend/dist, served by the backend at /
```

The production build sets its base path to `/anonymizer/` because the app is served
under that slug, so open the Vite dev server (not `:8400` directly) when working
locally. `node_modules/` and `dist/` are not committed.

## API

```bash
scripts/03_serve.sh     # or scripts\03_serve.ps1
```

Interactive documentation is then served at <http://127.0.0.1:8000/docs>, which
doubles as a demo surface. Models are loaded once at startup, not per request.

| Endpoint | Purpose |
|---|---|
| `POST /anonymize` | Anonymize a text; returns the result and the entities found |
| `GET /configs` | List the detector configurations available |
| `GET /health` | Liveness, and how many models are loaded |

```bash
curl -X POST http://127.0.0.1:8000/anonymize \
  -H "Content-Type: application/json" \
  -d '{"text": "Maria Lopez works at Contoso Ltd.", "config": "spacy+regex"}'
```

```json
{
  "config": "spacy+regex",
  "anonymized": "<PERSON> works at <ORG>",
  "entities": [
    {"start": 0, "end": 11, "label": "PERSON", "text": "Maria Lopez"},
    {"start": 21, "end": 33, "label": "ORG", "text": "Contoso Ltd."}
  ],
  "entity_counts": {"PERSON": 1, "ORG": 1},
  "original": null
}
```

- `config` is optional and defaults to the best-scoring configuration.
- Entity offsets are returned so a caller can highlight them in the original text.
- `include_original: true` echoes the input back, for a side-by-side before/after
  view. It is off by default: the input still contains the sensitive data, so
  returning it would place that text anywhere the response is stored or logged.

## Limits and abuse protection

Every request runs a language model on the host, so an unprotected public endpoint
is an easy way to exhaust a machine. Four independent limits apply, and **all of the
app-level ones are inert unless configured**, so running this repo locally gives an
unrestricted service.

| Limit | Where | Default | Purpose |
|---|---|---|---|
| Admission queue | reverse proxy | a handful of concurrent sessions | Caps how many visitors are active at once |
| Allowed session tiers | `ANONYMIZER_REQUIRE_TIER` | unset (open) | Restricts who may invoke a model |
| Maximum input length | `ANONYMIZER_MAX_TEXT_CHARS` | 20000 | A large paste is the cheapest way to burn CPU |
| Concurrent inferences | `ANONYMIZER_MAX_CONCURRENCY` | 2 | Sync handlers run in a 40-thread pool; without a bound, a burst could saturate the host |

Notes:

- `ANONYMIZER_REQUIRE_TIER` takes a comma-separated list (for example
  `admin,invited`). The session tier is supplied by the reverse proxy, which strips
  any value sent by the client, so it cannot be spoofed. When the variable is set and
  no tier arrives, the request is refused: it fails closed.
- Over the concurrency limit a request waits briefly, then gets `503` rather than
  queueing indefinitely.
- `GET /health` reports the limits actually in force, which is the quickest way to
  confirm a deployment is configured as intended.

## Hardware

Inference runs on the GPU when the installed PyTorch build supports one, and on the
CPU otherwise; `GET /health` reports which. The default install pins the **CPU-only**
PyTorch wheel, because the CUDA build adds gigabytes to a container image for
hardware the server does not have. To use a GPU, install a CUDA build instead:

```bash
uv pip install torch --index-url https://download.pytorch.org/whl/cu124
```

For the short texts this tool handles, the difference is marginal: the model is
`bert-base`, and a single request is dominated by fixed overhead rather than compute.

**Why FastAPI over Flask:** request validation comes from the type declarations
(pydantic returns a clear 422 on a bad body before the handler runs), the OpenAPI
`/docs` page is generated automatically and serves as the demo, the response shape
is declared rather than incidental, and ASGI leaves async available for slow model
calls. Flask would work, but each of those would need extra code or an add-on.

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
src/anonymizer/       the installed package
  dataset.py          load the labelled rows
  detectors/
    regex_rules.py    rule-based detector
    spacy_model.py    spaCy detector
    hf_model.py       HuggingFace transformer detector
  configs.py          the detector configurations, shared by benchmark and API
  pipeline.py         merge detectors, resolve overlapping spans
  spans.py            the Span type and placeholder replacement
  scoring.py          precision / recall / F1 and model comparison
  benchmark.py        run every configuration
  api.py              HTTP API
  report.py           generate report/REPORT.md
  charts.py           render the report charts
frontend/
  src/lib/            gateway admission, API client, types
  src/components/     the interactive demo
  src/App.tsx         page shell and content
scripts/              numbered setup, run and serve scripts (.sh and .ps1)
report/               generated benchmark report and charts
```

## Limitations

- The evaluation set is small, so per-label scores move a lot per entity.
- JOB and UNIVERSITY have no class in standard NER schemes and no fixed shape for
  a rule, so they need a gazetteer, hand-written patterns, or a zero-shot model.
- Phone and IBAN patterns are pragmatic heuristics, not full format specifications.
