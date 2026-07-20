# syntax=docker/dockerfile:1.7
# Build the frontend, then serve it + the API from the Python backend as one image.

# --- stage 1: build the SPA ---
FROM node:22-alpine AS frontend
WORKDIR /fe
COPY frontend/package*.json ./
RUN npm install --no-audit --no-fund
COPY frontend/ ./
# Picks up frontend/.env.production: gateway admission on, API base /anonymizer/api.
RUN npm run build

# --- stage 2: backend serving /api and the built SPA ---
FROM python:3.11-slim AS backend
COPY --from=ghcr.io/astral-sh/uv:0.11.29 /uv /usr/local/bin/uv
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    HF_HOME=/app/.cache/huggingface \
    ANONYMIZER_STATIC_DIR=/app/webroot

# Dependencies first so this layer is cached while application code changes.
# torch resolves to the CPU wheel (see pyproject), which keeps the image small.
COPY pyproject.toml uv.lock README.md ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev --no-install-project

# The anonymizer package itself is what the app imports at runtime, and the
# model-bake step needs it available before the final image is assembled.
COPY src/anonymizer ./src/anonymizer
ENV PYTHONPATH=/app/src

# Model weights are NOT baked into the image. They were, and it was the wrong call:
# the layer sits after `uv sync`, so any dependency change re-downloaded roughly two
# gigabytes, and unauthenticated Hugging Face requests are rate limited, which turned
# a rebuild into an hours-long stall.
#
# Instead HF_HOME points at a directory backed by a named volume (see the compose
# file), so the weights are fetched once on first start and survive every later
# rebuild. Populate it before starting the service with:
#
#     docker compose run --rm anonymizer /app/.venv/bin/python -m anonymizer.warm
#
# spaCy is the exception: it is installed as a pinned wheel from the lock file rather
# than downloaded at runtime, so it is already inside the image.

COPY --from=frontend /fe/dist ./webroot

EXPOSE 8400
# Call the environment's uvicorn directly rather than through `uv run`, so start-up
# never re-resolves dependencies or needs to write to the project directory.
CMD ["/app/.venv/bin/uvicorn", "anonymizer.api:app", "--host", "0.0.0.0", "--port", "8400"]
