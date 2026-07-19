"""Benchmark every model over the dataset and print each model's scorecard.

Each detector module exposes the same interface (`load()` and
`detect(model, text)`), so adding a model here is a one-line change.

    uv run python src/benchmark.py
"""

import hf_detector
import scoring
import spacy_detector
from anonymizer import anonymize_spans
from dataset import load_rows

# The models to benchmark, as (short name, detector module). Add more detector
# modules here later (e.g. spaCy lg/trf) and everything else adapts.
MODELS = [
    ("spaCy sm", spacy_detector),
    ("HF bert", hf_detector),
]


def evaluate(detector, model, rows) -> list[tuple[str, str]]:
    """Produce (result, expected) pairs for one detector over all rows."""
    pairs = []
    for row in rows:
        spans = detector.detect(model, row["text"])
        result = anonymize_spans(row["text"], spans)
        pairs.append((result, row["label"]))
    return pairs


def main() -> None:
    rows = load_rows()

    reports = {}
    for short_name, detector in MODELS:
        print(f"=== {short_name}: {detector.MODEL_NAME} ===")
        model = detector.load()
        reports[short_name] = scoring.score(evaluate(detector, model, rows))
        print()

    print("=== Comparison ===")
    scoring.compare(reports)


if __name__ == "__main__":
    main()
