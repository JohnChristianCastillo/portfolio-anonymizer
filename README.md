# portfolio-anonymizer

An NLP tool that detects and anonymizes sensitive entities (PII) in free text
using pre-trained named-entity-recognition models, and benchmarks multiple
models against a labelled dataset.

## Entities

PERSON, ORG, JOB, EMAIL_ADDRESS, LOCATION, AMOUNT, DATE_TIME, UNIVERSITY,
PHONE_NUMBER, URL, IBAN, SSN

## Approach

- Pre-trained NER models for unstructured entities (no training required to run)
- Regex for structured entities (email, phone, URL, IBAN, SSN, amount, date)
- Anonymize by replacing each detected entity with its `<LABEL>` placeholder
- Benchmark two or more models against a labelled dataset and report the results

## Status

In progress. Model 1 (spaCy) detection, label mapping, and anonymization are
working; the second model and the benchmark scorer are next.

## Models

This project uses public, pre-trained NER models. No model weights are committed
to the repo. Each model is declared as a dependency and downloaded from its
public source when you run `uv sync`, so nothing needs to be supplied by hand.

Currently used:

- spaCy `en_core_web_sm` (pinned in the lock file, installed automatically)

A second pre-trained model will be added so the two can be benchmarked against
each other. This list is updated as models are added.

## Dataset format

Benchmark datasets are kept local and are not committed. To replicate the
benchmark, provide a semicolon-separated CSV with two columns:

- `text` - the original text
- `label` - the same text with every sensitive entity replaced by its
  `<LABEL>` placeholder (see the entity labels listed above)

Example row:

```
text;label
John Smith works for Apple Inc.;<PERSON> works for <ORG>.
```
