"""Load the labelled benchmark dataset."""

import csv
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = PROJECT_ROOT / "data" / "benchmark.csv"


def load_rows(path: Path = DATA_FILE) -> list[dict[str, str]]:
    """Read the semicolon-separated benchmark file into a list of rows.

    Each row has `text` (the original) and `label` (the expected anonymized answer).
    """
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))
