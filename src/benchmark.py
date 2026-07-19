"""Benchmark every configuration over the dataset and print the scorecards.

Each detector module exposes the same interface (`load()` and
`detect(model, text)`), so a configuration is just a list of detectors in priority
order. Adding a model or a new combination is a one-line change to SYSTEMS.

    uv run python src/benchmark.py
"""

import hf_detector
import pipeline
import regex_detector
import scoring
import spacy_detector
from anonymizer import anonymize_spans
from dataset import load_rows

# Each system is (short name, detectors in priority order). Regex goes first so its
# precise, fixed-shape matches win any overlap against a model's guess.
SYSTEMS = [
    ("spaCy sm", [spacy_detector]),
    ("HF bert", [hf_detector]),
    ("spaCy+regex", [regex_detector, spacy_detector]),
    ("HF+regex", [regex_detector, hf_detector]),
]

# Models are expensive to load, so load each detector's model only once.
_loaded: dict = {}


def get_model(detector):
    """Load a detector's model once and reuse it."""
    if detector not in _loaded:
        _loaded[detector] = detector.load()
    return _loaded[detector]


def evaluate(detectors, rows) -> list[tuple[str, str]]:
    """Produce (result, expected) pairs for one configuration over all rows."""
    detectors_with_models = [(d, get_model(d)) for d in detectors]
    pairs = []
    for row in rows:
        spans = pipeline.detect_all(detectors_with_models, row["text"])
        pairs.append((anonymize_spans(row["text"], spans), row["label"]))
    return pairs


def main() -> None:
    rows = load_rows()

    reports = {}
    for name, detectors in SYSTEMS:
        print(f"=== {name} ===")
        reports[name] = scoring.score(evaluate(detectors, rows))
        print()

    print("=== Comparison ===")
    scoring.compare(reports)


if __name__ == "__main__":
    main()
