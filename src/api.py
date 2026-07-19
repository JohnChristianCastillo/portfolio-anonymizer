"""HTTP API exposing the anonymizer.

    uv run uvicorn api:app --app-dir src

Interactive documentation is served at /docs.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

import configs
import pipeline
from anonymizer import anonymize_spans

# Loaded models keyed by detector module. A transformer takes seconds to load, so
# every model is loaded once at startup rather than per request.
_models: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    for configuration in configs.CONFIGURATIONS:
        for detector in configuration.detectors:
            if detector not in _models:
                _models[detector] = detector.load()
    yield
    _models.clear()


app = FastAPI(
    title="portfolio-anonymizer",
    description="Detects and anonymizes sensitive entities (PII) in free text.",
    version="0.1.0",
    lifespan=lifespan,
)


class AnonymizeRequest(BaseModel):
    text: str = Field(min_length=1, description="Text to anonymize.")
    config: str = Field(
        default=configs.DEFAULT_KEY,
        description="Which detector configuration to use; see GET /configs.",
    )
    include_original: bool = Field(
        default=False,
        description=(
            "Echo the original text back, for a side-by-side view. Off by default: "
            "the input still contains the sensitive data, so returning it puts that "
            "text anywhere the response is stored or logged."
        ),
    )


class Entity(BaseModel):
    """One detected entity and where it was found."""

    start: int
    end: int
    label: str
    text: str


class AnonymizeResponse(BaseModel):
    config: str
    anonymized: str
    entities: list[Entity]
    entity_counts: dict[str, int] = Field(
        description="How many entities were found per label."
    )
    original: str | None = Field(
        default=None,
        description="The input text, present only when include_original was set.",
    )


@app.get("/health", summary="Liveness check")
def health() -> dict:
    return {"status": "ok", "models_loaded": len(_models)}


@app.get("/configs", summary="List the available detector configurations")
def list_configs() -> list[dict]:
    return [
        {
            "key": configuration.key,
            "label": configuration.label,
            "detectors": [d.MODEL_NAME for d in configuration.detectors],
            "default": configuration.key == configs.DEFAULT_KEY,
        }
        for configuration in configs.CONFIGURATIONS
    ]


@app.post("/anonymize", response_model=AnonymizeResponse, summary="Anonymize a text")
def anonymize(request: AnonymizeRequest) -> AnonymizeResponse:
    """Replace every detected entity with its `<LABEL>` placeholder.

    Returns the anonymized text plus the entities found, with character offsets so a
    caller can highlight them in the original.
    """
    configuration = configs.by_key(request.config)
    if configuration is None:
        known = ", ".join(c.key for c in configs.CONFIGURATIONS)
        raise HTTPException(
            status_code=422,
            detail=f"Unknown config '{request.config}'. Available: {known}",
        )

    detectors_with_models = [(d, _models[d]) for d in configuration.detectors]
    spans = pipeline.detect_all(detectors_with_models, request.text)

    entities = [
        Entity(start=start, end=end, label=label, text=request.text[start:end])
        for start, end, label in sorted(spans)
    ]

    counts: dict[str, int] = {}
    for entity in entities:
        counts[entity.label] = counts.get(entity.label, 0) + 1

    return AnonymizeResponse(
        config=configuration.key,
        anonymized=anonymize_spans(request.text, spans),
        entities=entities,
        entity_counts=counts,
        original=request.text if request.include_original else None,
    )
