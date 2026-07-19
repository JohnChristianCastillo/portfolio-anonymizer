"""Load the labelled benchmark dataset."""

import csv
from pathlib import Path

# src/anonymizer/dataset.py -> up through anonymizer, src, to the project root.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_FILE = PROJECT_ROOT / "data" / "benchmark.csv"


def load_rows(path: Path = DATA_FILE) -> list[dict[str, str]]:
    """Read the semicolon-separated benchmark file into a list of rows.

    Each row has `text` (the original) and `label` (the expected anonymized answer).
    """
    if not path.exists():
        raise FileNotFoundError(
            f"No benchmark file at {path}\n"
            "Datasets are not committed. Place a semicolon-separated CSV with "
            "'text' and 'label' columns at that path, or pass a different one. "
            "The README describes the expected format."
        )
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))
