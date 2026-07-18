"""Sub-step A: turn Model 1 (spaCy) entities into anonymized text.

For each benchmark row:
  1. run spaCy NER,
  2. map spaCy's native labels to the 12-label scheme,
  3. replace each mapped entity span with its <LABEL> placeholder,
  4. print the resulting anonymized output next to the expected answer.

No scoring yet - this is the eyeball check. Run with:

    uv run python src/anonymize_spacy.py
"""

import csv
from pathlib import Path

import spacy
from spacy.tokens import Doc

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = PROJECT_ROOT / "data" / "benchmark.csv"

MODEL_NAME = "en_core_web_sm"

# Map spaCy's OntoNotes labels to our target scheme. Labels not listed here are
# left in the text untouched (e.g. CARDINAL, NORP, ORDINAL).
SPACY_LABEL_MAP = {
    "PERSON": "PERSON",
    "ORG": "ORG",
    "GPE": "LOCATION",
    "LOC": "LOCATION",
    "DATE": "DATE_TIME",
    "TIME": "DATE_TIME",
    "MONEY": "AMOUNT",
}


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def anonymize(doc: Doc, text: str, label_map: dict[str, str]) -> str:
    """Replace each mapped entity span with its <LABEL> placeholder.

    Spans are replaced right-to-left (highest start offset first) so each
    replacement does not shift the offsets of spans still to be replaced.

    (= manipulating the text in place changes indexes, to be resistant to this
    manipulate back end to front)
    """
    # Collect (start, end, label) only for entities whose label we target.
    spans = []
    for ent in doc.ents:
        mapped = label_map.get(ent.label_)
        if mapped is not None:
            spans.append((ent.start_char, ent.end_char, mapped))

    # Sorting the tuples in reverse orders them by start position, highest first
    # (a tuple sorts by its first element), giving the right-to-left order.
    spans.sort(reverse=True)

    result = text
    for start, end, label in spans:
        result = result[:start] + f"<{label}>" + result[end:]
    return result


def main() -> None:
    print(f"Loading model: {MODEL_NAME}")
    nlp = spacy.load(MODEL_NAME)

    rows = load_rows(DATA_FILE)
    print(f"Loaded {len(rows)} rows from {DATA_FILE.name}\n")

    for i, row in enumerate(rows, start=1):
        text = row["text"]
        doc = nlp(text)
        result = anonymize(doc, text, SPACY_LABEL_MAP)

        print(f"--- Row {i} ---")
        print(f"RESULT  : {result}")
        print(f"EXPECTED: {row['label']}")
        print()


if __name__ == "__main__":
    main()
