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

Scaffold. Implementation in progress.

## Models

No model weights are shipped with this repo. To run it, supply your own
pre-trained NER model (for example a spaCy or Hugging Face model), downloaded
and run locally.

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
