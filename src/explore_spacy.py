"""Exploration: run Model 1 (spaCy en_core_web_sm) over the benchmark rows and
print the raw named entities it finds.

This is a throwaway look at how much a single pre-trained model covers, before we
add label mapping, regex, or scoring. Run with:

    uv run python src/explore_spacy.py
"""

import csv
from pathlib import Path

import spacy

# Project root is one level up from this src/ folder.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = PROJECT_ROOT / "data" / "benchmark.csv"

MODEL_NAME = "en_core_web_sm"


def load_rows(path: Path) -> list[dict[str, str]]:
    """Read the semicolon-separated benchmark file into a list of rows.

    Each row has a `text` (original) and a `label` (the gold anonymized version).
    """
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        return list(reader)


def main() -> None:
    print(f"Loading model: {MODEL_NAME}")
    nlp = spacy.load(MODEL_NAME)

    rows = load_rows(DATA_FILE)
    print(f"Loaded {len(rows)} rows from {DATA_FILE.name}\n")

    for i, row in enumerate(rows, start=1):
        text = row["text"]
        doc = nlp(text)
        entities = [(ent.text, ent.label_) for ent in doc.ents]

        print(f"--- Row {i} ---")
        print(f"TEXT : {text}")
        print(f"GOLD : {row['label']}")
        print(f"SPACY: {entities}")
        print()


if __name__ == "__main__":
    main()
