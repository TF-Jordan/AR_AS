# ==============================================================================
# Dockerfile - AR_AS Système Complet
# ==============================================================================
# Avec wheels locaux (rapide): mkdir -p wheels && pip wheel -w wheels/ -r requirements.txt
# Sans wheels (télécharge):    docker compose build
# ==============================================================================

FROM python:3.11-slim

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

# Copier requirements
COPY requirements.txt .

# Copier wheels si présents (utiliser * pour éviter erreur si absent)
COPY wheel[s]/ /wheels/

# Installer les dépendances
RUN pip install --upgrade pip && \
    if [ -d "/wheels" ] && [ "$(ls -A /wheels 2>/dev/null)" ]; then \
        echo "=== Installation depuis wheels locaux ===" && \
        pip install --find-links=/wheels -r requirements.txt && \
        rm -rf /wheels; \
    else \
        echo "=== Installation depuis PyPI ===" && \
        pip install -r requirements.txt; \
    fi

# Copier le code source
COPY src/ /app/src/

# Créer les dossiers nécessaires
RUN mkdir -p /app/logs /app/data && \
    chown -R appuser:appgroup /app

USER appuser
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "src.api.app:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "4", \
     "--log-level", "info"]
