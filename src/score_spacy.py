"""Score Model 1 (spaCy) against the benchmark.

Runs spaCy over every benchmark row, anonymizes each one, then reports per-label
precision / recall / F1 using the reusable scorer. Run with:

    uv run python src/score_spacy.py
"""

import spacy

import scoring
from anonymize_spacy import (
    DATA_FILE,
    MODEL_NAME,
    SPACY_LABEL_MAP,
    anonymize,
    load_rows,
)


def main() -> None:
    print(f"Loading model: {MODEL_NAME}")
    nlp = spacy.load(MODEL_NAME)
    rows = load_rows(DATA_FILE)

    pairs: list[tuple[str, str]] = []
    for row in rows:
        doc = nlp(row["text"])
        result = anonymize(doc, row["text"], SPACY_LABEL_MAP)
        pairs.append((result, row["label"]))

    print(f"Scored {len(pairs)} rows for {MODEL_NAME}\n")
    scoring.score(pairs)


if __name__ == "__main__":
    main()
