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
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev

# Copy only the model-loading code needed to bake the HuggingFace cache. Keeping
# this separate from the rest of the app source means unrelated API/frontend edits
# do not force the ~400 MB model download layer to rebuild.
COPY src/anonymizer/__init__.py ./src/anonymizer/__init__.py
COPY src/anonymizer/spans.py ./src/anonymizer/spans.py
COPY src/anonymizer/detectors ./src/anonymizer/detectors

# Bake the transformer weights into the image. Without this the container would
# download ~400 MB from the Hugging Face hub on first request, so a cold start (or
# an offline host) would fail rather than just being slow.
RUN /app/.venv/bin/python -c "from anonymizer.detectors import hf_model; hf_model.load()"

COPY src ./src
COPY --from=frontend /fe/dist ./webroot

EXPOSE 8400
# Call the environment's uvicorn directly rather than through `uv run`, so start-up
# never re-resolves dependencies or needs to write to the project directory.
CMD ["/app/.venv/bin/uvicorn", "anonymizer.api:app", "--host", "0.0.0.0", "--port", "8400"]
