# Backend container for Speakly Phase 1
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

WORKDIR /app

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements-dev.txt /tmp/requirements-dev.txt
COPY backend/requirements.txt /tmp/requirements.txt

RUN pip install -r /tmp/requirements-dev.txt

COPY backend /app/backend

# Ensure data directories exist at runtime
RUN mkdir -p /app/backend/data /app/backend/logs /app/backend/storage/audio

EXPOSE 8000

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
