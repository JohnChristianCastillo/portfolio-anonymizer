"""Benchmark every configuration over the dataset and print the scorecards.

Each detector module exposes the same interface (`load()` and
`detect(model, text)`), so a configuration is just a list of detectors in priority
order. Adding a model or a new combination is a one-line change in configs.py.

The required two-model comparison is reported first and on its own. Anything added
afterwards is reported separately, so the two are never conflated.

    uv run anonymizer-benchmark

Include the zero-shot configurations, which need a package that is deliberately not
in the lock file:

    uv run --with gliner anonymizer-benchmark
"""

from . import configs, pipeline, scoring
from .dataset import load_rows
from .spans import anonymize_spans

# Kept for backwards compatibility with anything referring to the old flat list.
SYSTEMS = [(c.label, c.detectors) for c in configs.CORE_CONFIGURATIONS]

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

    core = {}
    for configuration in configs.CORE_CONFIGURATIONS:
        print(f"=== {configuration.label} ===")
        core[configuration.label] = scoring.score(evaluate(configuration.detectors, rows))
        print()

    # The models on their own. This is the comparison the exercise asked for: the
    # rule layer covers only five of the twelve labels, so including it would measure
    # a system rather than a model.
    print("###  Required comparison: the two models, measured alone  ###")
    scoring.compare(
        {c.label: core[c.label] for c in configs.models_only(configs.CORE_CONFIGURATIONS)}
    )

    print("\n###  Same models, with the rule layer added (a system, not a model)  ###")
    scoring.compare(
        {c.label: core[c.label] for c in configs.with_rules(configs.CORE_CONFIGURATIONS)}
    )

    extended = configs.runnable(configs.EXTENDED_CONFIGURATIONS)
    skipped = [c for c in configs.EXTENDED_CONFIGURATIONS if not c.available()]

    if extended:
        print("\n\n###  Extended exploration, beyond the required comparison  ###\n")
        for configuration in extended:
            print(f"=== {configuration.label} ===")
            core[configuration.label] = scoring.score(
                evaluate(configuration.detectors, rows)
            )
            print()
        print("=== Comparison, all configurations ===")
        scoring.compare(core)

    if skipped:
        names = ", ".join(f"{c.label} (needs {c.requires})" for c in skipped)
        print(f"\nSkipped, optional dependency not installed: {names}")
        print("Run with: uv run --with gliner anonymizer-benchmark")


if __name__ == "__main__":
    main()
