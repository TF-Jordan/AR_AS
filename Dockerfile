# ==============================================================================
# Dockerfile - AR_AS (Optimisé multi-stage avec PyTorch CPU-only)
# ==============================================================================
# Estimation: ~1.5 GB au lieu de ~14 GB
#
# Optimisations appliquées:
#   1. Multi-stage build (les wheels ne restent pas dans l'image finale)
#   2. PyTorch CPU-only (~250 MB au lieu de ~2.5 GB avec CUDA)
#   3. Suppression de torchvision/torchaudio (non utilisés)
#   4. COPY --chown au lieu de RUN chown (évite duplication de couche)
#   5. Installation directe depuis PyPI + index CPU (plus besoin de wheels/)
#
# Build: docker compose build
# ==============================================================================

# ---- Stage 1: Builder ----
FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

COPY requirements.txt .

# Installer les dépendances dans un virtualenv isolé
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Installer les dépendances système nécessaires à la compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Installer PyTorch CPU-only d'abord (depuis l'index PyTorch CPU)
RUN pip install \
    torch==2.9.1+cpu \
    --index-url https://download.pytorch.org/whl/cpu

# Installer le reste des dépendances (sans torch/torchvision/torchaudio)
RUN pip install \
    --no-deps sentence-transformers==5.2.0 && \
    pip install -r requirements.txt \
    --index-url https://download.pytorch.org/whl/cpu \
    --extra-index-url https://pypi.org/simple/

# ---- Stage 2: Runtime ----
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dépendances système runtime uniquement
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Créer utilisateur non-root
RUN groupadd -r appgroup && \
    useradd -r -g appgroup -u 1000 -d /app -s /bin/bash appuser && \
    mkdir -p /app/logs /app/data && \
    chown -R appuser:appgroup /app

# Copier le virtualenv depuis le builder (pas de couche wheels résiduelle)
COPY --from=builder --chown=appuser:appgroup /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copier le code source avec --chown (évite une couche RUN chown séparée)
COPY --chown=appuser:appgroup src/ /app/src/

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--log-level", "info"]
