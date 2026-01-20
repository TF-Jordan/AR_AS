# ==============================================================================
# Dockerfile - AR_AS Système Complet
# ==============================================================================
# Build avec wheels locaux (rapide, pas de téléchargement):
#   1. ./scripts/prepare-wheels.sh
#   2. docker compose build
#
# Build standard (télécharge les dépendances):
#   docker compose build
# ==============================================================================

FROM python:3.11-slim AS base

# Variables d'environnement
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=300

WORKDIR /app

# Dépendances système
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Créer utilisateur non-root
RUN groupadd -r appgroup && \
    useradd -r -g appgroup -u 1000 -d /app -s /bin/bash appuser

# ==============================================================================
# Installation des dépendances
# ==============================================================================

# Copier requirements
COPY requirements.txt .

# Copier wheels locaux (si présents)
COPY wheels/ /wheels/

# Installer les dépendances
# Utilise les wheels locaux s'ils existent, sinon télécharge
RUN pip install --upgrade pip && \
    if [ -d "/wheels" ] && [ "$(ls -A /wheels 2>/dev/null)" ]; then \
        echo "Installation depuis wheels locaux..." && \
        pip install --no-index --find-links=/wheels -r requirements.txt; \
    else \
        echo "Installation depuis PyPI..." && \
        pip install -r requirements.txt; \
    fi && \
    rm -rf /wheels

# ==============================================================================
# Application
# ==============================================================================

# Copier le code source
COPY src/ /app/src/

# Créer les dossiers nécessaires
RUN mkdir -p /app/logs /app/data && \
    chown -R appuser:appgroup /app

# Utilisateur non-root
USER appuser

# Port API
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Commande par défaut (API)
CMD ["uvicorn", "src.api.app:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "4", \
     "--log-level", "info"]
