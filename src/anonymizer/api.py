"""HTTP API exposing the anonymizer, plus the built front end.

    uv run uvicorn api:app --app-dir src --port 8400

Interactive documentation is served at /docs.

Data endpoints live under /api. Behind the portfolio gateway that prefix is what
requires an admitted session, so model inference sits behind the queue while the
page itself stays open to anyone.
"""

import os
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import APIRouter, FastAPI, Header, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import configs, pipeline
from .detectors import hf_model
from .spans import anonymize_spans

# Loaded models keyed by detector module. A transformer takes seconds to load, so
# every model is loaded once at startup rather than per request.
_models: dict = {}

# --- limits -----------------------------------------------------------------
# Running a model on someone else's text is expensive, so a public deployment needs
# more than the gateway's admission queue, which caps concurrent visitors but not
# what each one asks for. All three limits are inert unless configured, so anyone
# running this repo locally gets an unrestricted service.

# Longest accepted input for public and invited sessions. Admin is exempt.
LIMITED_MAX_TEXT_CHARS = int(os.environ.get("ANONYMIZER_MAX_TEXT_CHARS", "10000"))

# Sync handlers run in a thread pool (40 threads by default), so without a bound
# that many inferences could run at once. Requests over the limit wait briefly and
# are then refused rather than queueing forever.
_MAX_CONCURRENT = int(os.environ.get("ANONYMIZER_MAX_CONCURRENCY", "2"))
_ACQUIRE_TIMEOUT_SECONDS = 15
_inference_slots = threading.BoundedSemaphore(_MAX_CONCURRENT)


# Which configurations this instance serves, comma separated (see GET /configs).
# Every model stays resident once loaded, and all of them together need roughly
# 1.7 GB, which is more than a small container is usually given. Empty means serve
# everything, which is how a local run behaves.
_REQUESTED_CONFIGS = os.environ.get("ANONYMIZER_CONFIGS", "").strip()

# Session tiers allowed to call the model, comma separated (admin, invited,
# anonymous). Empty means open to everyone. The gateway verifies the tier and sends
# it as X-Session-Tier, stripping any value supplied by the client, so this cannot
# be spoofed from outside.
_REQUIRED_TIERS = {
    tier.strip()
    for tier in os.environ.get("ANONYMIZER_REQUIRE_TIER", "").split(",")
    if tier.strip()
}


def _check_tier(session_tier: str | None) -> None:
    """Reject callers whose session tier is not allowed for this deployment."""
    if not _REQUIRED_TIERS:
        return  # unconfigured: open, which is how a local run behaves
    if session_tier not in _REQUIRED_TIERS:
        raise HTTPException(
            status_code=403,
            detail=(
                "This deployment is limited to "
                f"{' or '.join(sorted(_REQUIRED_TIERS))} sessions. "
                "Run the project locally for unrestricted access."
            ),
        )


def _text_limit_for(session_tier: str | None) -> int | None:
    if not _REQUIRED_TIERS:
        return None
    if session_tier == "admin":
        return None
    return LIMITED_MAX_TEXT_CHARS


def _enabled_configurations() -> list[configs.Configuration]:
    """The configurations this instance serves.

    The default is always included, so the service can never start up unable to
    answer its own default, and an unrecognised list falls back to serving
    everything rather than leaving the app with nothing to offer.
    """
    available = configs.runnable(configs.CONFIGURATIONS)
    if not _REQUESTED_CONFIGS:
        return available

    wanted = {key.strip() for key in _REQUESTED_CONFIGS.split(",") if key.strip()}
    wanted.add(configs.DEFAULT_KEY)
    return [c for c in available if c.key in wanted] or available


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Only the configurations this instance serves, so a memory-constrained
    # deployment does not load models it will never be asked for.
    for configuration in _enabled_configurations():
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


# Data endpoints. The /api prefix is what the gateway gates on.
api = APIRouter(prefix="/api")


@app.get("/health", summary="Liveness check")
def health() -> dict:
    """Liveness, plus the limits actually in force, to confirm a deployment."""
    return {
        "status": "ok",
        "models_loaded": len(_models),
        "device": "gpu" if hf_model.device_index() >= 0 else "cpu",
        "limits": {
            "limited_text_chars": LIMITED_MAX_TEXT_CHARS,
            "admin_text_chars": "unlimited",
            "max_concurrency": _MAX_CONCURRENT,
            "required_tiers": sorted(_REQUIRED_TIERS) or "open",
        },
    }


@api.get("/configs", summary="List the available detector configurations")
def list_configs() -> list[dict]:
    return [
        {
            "key": configuration.key,
            "label": configuration.label,
            "detectors": [d.MODEL_NAME for d in configuration.detectors],
            "default": configuration.key == configs.DEFAULT_KEY,
            # False for configurations added after the required two-model comparison,
            # so a caller can present them separately.
            "core": configuration.core,
        }
        # Only what this deployment can actually run.
        for configuration in _enabled_configurations()
    ]


@api.post("/anonymize", response_model=AnonymizeResponse, summary="Anonymize a text")
def anonymize(
    request: AnonymizeRequest,
    x_session_tier: str | None = Header(default=None, include_in_schema=False),
) -> AnonymizeResponse:
    """Replace every detected entity with its `<LABEL>` placeholder.

    Returns the anonymized text plus the entities found, with character offsets so a
    caller can highlight them in the original.
    """
    _check_tier(x_session_tier)

    text_limit = _text_limit_for(x_session_tier)
    if text_limit is not None and len(request.text) > text_limit:
        raise HTTPException(
            status_code=413,
            detail=(
                f"This deployment limits public and invited sessions to {text_limit} "
                "characters per submission. Admin sessions are unlimited."
            ),
        )

    configuration = configs.by_key(request.config)
    if configuration is not None and not configuration.available():
        raise HTTPException(
            status_code=422,
            detail=(
                f"Config '{request.config}' needs the optional "
                f"'{configuration.requires}' package, which is not installed here."
            ),
        )
    if configuration is None:
        known = ", ".join(c.key for c in _enabled_configurations())
        raise HTTPException(
            status_code=422,
            detail=f"Unknown config '{request.config}'. Available: {known}",
        )

    detectors_with_models = [(d, _models[d]) for d in configuration.detectors]

    # Bound how many inferences run at once, so a burst cannot saturate the host.
    if not _inference_slots.acquire(timeout=_ACQUIRE_TIMEOUT_SECONDS):
        raise HTTPException(
            status_code=503,
            detail="The service is busy running other requests. Try again shortly.",
        )
    try:
        spans = pipeline.detect_all(detectors_with_models, request.text)
    finally:
        _inference_slots.release()

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


app.include_router(api)

# Serve the built front end as the app shell. Mounted last so it never shadows the
# API routes, and skipped when the front end has not been built yet (plain dev).
# ANONYMIZER_STATIC_DIR lets the container point at wherever it copied the build.
_FRONTEND_DIST = Path(
    os.environ.get(
        "ANONYMIZER_STATIC_DIR",
        Path(__file__).resolve().parents[2] / "frontend" / "dist",
    )
)
if _FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=_FRONTEND_DIST, html=True), name="frontend")
