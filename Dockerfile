# ==============================================================================
# Dockerfile Modulaire pour AR_AS
# ==============================================================================
# USAGE:
#   Module 4 uniquement (léger ~200MB):
#     docker build --target api-module4 -t ar-as-module4 .
#
#   Système complet (lourd ~4GB):
#     docker build --target api-full -t ar-as-full .
#
#   Développement:
#     docker build --target development -t ar-as-dev .
# ==============================================================================

# ==============================================================================
# BASE COMMUNE
# ==============================================================================
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=300 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

WORKDIR /app

# Dépendances système minimales
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Créer utilisateur non-root
RUN groupadd -r appgroup && \
    useradd -r -g appgroup -u 1000 -d /app -s /bin/bash appuser

# ==============================================================================
# STAGE: Dependencies Module 4 (LÉGER - ~50MB de packages)
# ==============================================================================
FROM base AS deps-module4

COPY requirements-module4.txt .

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements-module4.txt

# ==============================================================================
# STAGE: Dependencies Full (LOURD - ~3GB avec torch)
# ==============================================================================
FROM base AS deps-full

# Installer les dépendances de build pour psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ==============================================================================
# STAGE: Application Module 4
# ==============================================================================
FROM deps-module4 AS app-module4

# Copier uniquement le code nécessaire pour Module 4
COPY src/api/ /app/src/api/
COPY src/modules/module4_livreur_ranking/ /app/src/modules/module4_livreur_ranking/
COPY src/core/ /app/src/core/
COPY src/__init__.py /app/src/

# Créer les dossiers nécessaires
RUN mkdir -p /app/logs && \
    chown -R appuser:appgroup /app

# ==============================================================================
# STAGE: Application Full
# ==============================================================================
FROM deps-full AS app-full

# Copier tout le code source
COPY src/ /app/src/

# Créer les dossiers pour les modèles
RUN mkdir -p \
    /app/src/modules/module1_sentiment/models \
    /app/src/modules/module2_recommendation/models \
    /app/logs \
    /app/data && \
    chown -R appuser:appgroup /app

# ==============================================================================
# TARGET: API Module 4 (Production - Léger)
# ==============================================================================
FROM app-module4 AS api-module4

USER appuser
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/livreur-ranking/health || exit 1

CMD ["uvicorn", "src.api.app:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "4", \
     "--log-level", "info"]

# ==============================================================================
# TARGET: API Full (Production - Complet)
# ==============================================================================
FROM app-full AS api-full

USER appuser
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "src.api.app:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "4", \
     "--log-level", "info"]

# ==============================================================================
# TARGET: Celery Worker (Système complet uniquement)
# ==============================================================================
FROM app-full AS worker

USER appuser

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD celery -A src.modules.module3_orchestration.celery_app inspect ping || exit 1

CMD ["celery", "-A", "src.modules.module3_orchestration.celery_app", "worker", \
     "--loglevel=info", \
     "--concurrency=4", \
     "--max-tasks-per-child=1000"]

# ==============================================================================
# TARGET: Celery Beat (Scheduler)
# ==============================================================================
FROM app-full AS beat

USER appuser

CMD ["celery", "-A", "src.modules.module3_orchestration.celery_app", "beat", \
     "--loglevel=info", \
     "--pidfile=/tmp/celerybeat.pid"]

# ==============================================================================
# TARGET: Flower (Monitoring Celery)
# ==============================================================================
FROM app-full AS flower

USER appuser
EXPOSE 5555

CMD ["celery", "-A", "src.modules.module3_orchestration.celery_app", "flower", \
     "--port=5555", \
     "--persistent=True"]

# ==============================================================================
# TARGET: Development (avec hot-reload)
# ==============================================================================
FROM app-module4 AS development

# Installer outils de dev
RUN pip install --no-cache-dir \
    watchdog \
    ipython \
    black \
    flake8 \
    pytest \
    pytest-asyncio

USER appuser
EXPOSE 8000

CMD ["uvicorn", "src.api.app:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--reload", \
     "--log-level", "debug"]

# ==============================================================================
# TARGET: Development Full (avec hot-reload + tous modules)
# ==============================================================================
FROM app-full AS development-full

# Installer outils de dev
RUN pip install --no-cache-dir \
    watchdog \
    ipython \
    black \
    flake8 \
    pytest \
    pytest-asyncio \
    pytest-cov

USER appuser
EXPOSE 8000

CMD ["uvicorn", "src.api.app:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--reload", \
     "--log-level", "debug"]

# ==============================================================================
# LABELS
# ==============================================================================
LABEL maintainer="AR_AS Team" \
      version="2.0.0" \
      description="AR_AS - Modular Docker Build (Module4/Full)"
