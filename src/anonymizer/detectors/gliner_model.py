"""Zero-shot detector (GLiNER).

Conventional NER models can only emit the labels they were trained on, which is why
JOB and UNIVERSITY score zero for every other configuration here: no standard scheme
contains those classes. A zero-shot model is given the label names at inference time
instead, so it can be asked for them directly.

Optional on purpose. The `gliner` package pins an older `transformers` than the rest
of the project, and installing it would change the environment the required
two-model comparison was measured in. It is therefore never added to the lock file;
run it in a throwaway overlay instead:

    uv run --with gliner anonymizer-benchmark

Without the package installed, `is_available()` is False and the benchmark simply
reports this configuration as skipped.
"""

from ..spans import Span

MODEL_NAME = "urchade/gliner_base"

# Zero-shot labels are natural-language prompts, so each one is written the way the
# model is most likely to understand it, then mapped onto the target scheme.
PROMPT_MAP = {
    "person": "PERSON",
    "organization": "ORG",
    "location": "LOCATION",
    "job title": "JOB",
    "university": "UNIVERSITY",
    "email address": "EMAIL_ADDRESS",
    "phone number": "PHONE_NUMBER",
    "date": "DATE_TIME",
    "amount of money": "AMOUNT",
}

PROMPTS = list(PROMPT_MAP)

# Below this confidence a prediction is discarded. Zero-shot output is noisier than
# a fine-tuned model's, because nothing was trained on these exact label names.
MIN_SCORE = 0.5


def is_available() -> bool:
    """Whether the optional `gliner` package is installed."""
    try:
        import gliner  # noqa: F401
    except ImportError:
        return False
    return True


def load(model_name: str = MODEL_NAME):
    """Load the zero-shot model, or raise a clear error if it is not installed."""
    try:
        from gliner import GLiNER
    except ImportError as exc:
        raise ImportError(
            "The gliner package is not installed. It is deliberately kept out of the "
            "lock file because it pins an older transformers than the rest of the "
            "project. Run the benchmark with: uv run --with gliner anonymizer-benchmark"
        ) from exc
    return GLiNER.from_pretrained(model_name)


def detect(model, text: str) -> list[Span]:
    """Return (start, end, label) spans for the prompted entity types in `text`."""
    spans: list[Span] = []
    for entity in model.predict_entities(text, PROMPTS):
        if entity.get("score", 1.0) < MIN_SCORE:
            continue
        label = PROMPT_MAP.get(entity["label"])
        if label is not None:
            spans.append((int(entity["start"]), int(entity["end"]), label))
    return spans
