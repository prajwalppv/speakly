# Backend container for Speakly Phase 1
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_LINK_MODE=copy

WORKDIR /app/backend

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        build-essential \
        curl \
        ffmpeg \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv as our package manager
RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
    && mv /root/.local/bin/uv /usr/local/bin/uv \
    && rm -rf /root/.local

# Copy dependency manifests early for better layer caching
COPY backend/pyproject.toml backend/uv.lock ./

# Resolve and download the dependency graph (including dev extras for tests)
RUN uv sync --frozen --extra dev --no-install-project --python 3.11

# Copy the full application source
COPY backend /app/backend

# Install the project itself into the managed environment
RUN uv sync --frozen --extra dev --python 3.11

ENV VIRTUAL_ENV=/opt/venv
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"

# Ensure data directories exist at runtime
RUN mkdir -p /app/backend/data /app/backend/logs /app/backend/storage/audio

EXPOSE 8000

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
