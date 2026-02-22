# ==============================================================================
# Dockerfile - AR_AS RaaS Platform (Multi-stage, PyTorch CPU-only)
# ==============================================================================

# ---- Stage 1: Builder ----
FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

COPY requirements.txt .

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install PyTorch CPU-only first
RUN pip install \
    torch==2.9.1+cpu \
    --index-url https://download.pytorch.org/whl/cpu

# Install rest of dependencies excluding torch
RUN grep -v "^torch==" requirements.txt > requirements-no-torch.txt && \
    pip install --no-deps sentence-transformers==5.2.0 && \
    pip install -r requirements-no-torch.txt

# ---- Stage 2: Runtime ----
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

RUN groupadd -r appgroup && \
    useradd -r -g appgroup -u 1000 -d /app -s /bin/bash appuser && \
    mkdir -p /app/logs /app/data && \
    chown -R appuser:appgroup /app

COPY --from=builder --chown=appuser:appgroup /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY --chown=appuser:appgroup src/ /app/src/
COPY --chown=appuser:appgroup main.py /app/main.py

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--log-level", "info"]
