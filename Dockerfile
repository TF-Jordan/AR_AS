# ==============================================================================
# Dockerfile - AR_AS (Optimisé avec wheels pré-compilés)
# ==============================================================================
# PREREQUIS: Créer le dossier wheels avec vos packages locaux
#   pip wheel -w wheels/ -r requirements.txt
#
# Build: docker compose build
# ==============================================================================

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dépendances système minimales (runtime uniquement, pas de compilation)
# - curl: pour healthchecks
# - libpq5: runtime pour psycopg2 (pas libpq-dev)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Créer utilisateur non-root
RUN groupadd -r appgroup && \
    useradd -r -g appgroup -u 1000 -d /app -s /bin/bash appuser

# Copier requirements et wheels
COPY requirements.txt .
COPY wheels/ /wheels/

# Installer depuis les wheels locaux (télécharge uniquement les manquants)
# On installe les paquets en utilisant UNIQUEMENT le dossier local
RUN pip install --no-index --find-links=/wheels -r requirements.txt && \
    rm -rf /wheels

# Copier le code source
COPY src/ /app/src/

# Permissions
RUN mkdir -p /app/logs /app/data && \
    chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--log-level", "info"]
