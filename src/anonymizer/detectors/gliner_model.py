"""Zero-shot detector (GLiNER).

Conventional NER models can only emit the labels they were trained on, which is why
JOB and UNIVERSITY score zero for every other configuration here: no standard scheme
contains those classes. A zero-shot model is given the label names at inference time
instead, so it can be asked for them directly.

This was once an optional dependency: `gliner` pinned an older `transformers` than
the rest of the project, so installing it would have changed the environment the
required two-model comparison was measured in. Later versions lifted that pin, so it
is now an ordinary dependency. `is_available()` is kept so the configurations still
degrade to being skipped rather than failing if the package is ever absent.
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
            "The gliner package is not installed. It is a normal dependency of this "
            "project, so `uv sync` should provide it."
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
