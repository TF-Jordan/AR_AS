# PLAN D'ACTION - MONITORING ELK COMPLET

## 🎯 Objectif
Assurer un monitoring complet du système en utilisant **UNIQUEMENT la stack ELK** (Elasticsearch, Logstash, Kibana) + Elastic APM + Filebeat + Metricbeat.

**⚠️ IMPORTANT:** Nous n'utilisons PAS Prometheus. Toutes les métriques seront collectées via structured logging et Elastic APM.

---

## 📊 État Actuel - Résumé

### ✅ CE QUI FONCTIONNE
- Infrastructure ELK complète (Elasticsearch 8.11, Logstash, Kibana, Filebeat)
- Elastic APM Server configuré et actif
- Logging structuré JSON avec `structlog` + `python-json-logger`
- Pipeline Logstash avec filtrage et enrichissement
- 3 dashboards Kibana configurés
- 154 appels de logging dans le code

### ❌ PROBLÈMES CRITIQUES À CORRIGER
1. **Middleware non enregistrés** - `RequestLoggingMiddleware` et `CorrelationIdMiddleware` définis mais jamais utilisés dans l'app
2. **Correlation ID non propagé** - Ne traverse pas Celery/Cache/Database
3. **Database queries non loggés** en production (`echo=debug`)
4. **Métriques applicatives manquantes** - Cache hit/miss, ML inference time, Vector search latency
5. **Pas de spans APM personnalisés** - Opérations critiques non instrumentées

---

## 🚀 PHASE 1 - CORRECTIONS CRITIQUES (Priorité IMMÉDIATE)

### 1.1 Enregistrer les Middleware Manquants

**Fichier à modifier:** `src/api/app.py`

**Objectif:** Activer le logging de toutes les requêtes HTTP avec durée, status code, et correlation ID.

**Actions:**
```python
# Dans create_app(), après la création de l'app FastAPI
from src.api.middleware import RequestLoggingMiddleware, CorrelationIdMiddleware

# Ordre d'ajout des middleware (important !)
# 1. CORS (déjà présent)
# 2. Correlation ID (nouveau)
app.add_middleware(CorrelationIdMiddleware)

# 3. Request Logging (nouveau)
app.add_middleware(RequestLoggingMiddleware)

# 4. Rate Limiter (déjà présent)
# 5. Elastic APM (déjà présent)
```

**Logs produits:**
```json
{
  "timestamp": 1234567890.123,
  "level": "INFO",
  "logger": "api.middleware",
  "service": "Sentiment Recommendation System",
  "message": "Request completed",
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "method": "POST",
  "path": "/api/v1/recommendations",
  "status_code": 200,
  "duration_seconds": 0.345,
  "client_ip": "192.168.1.100"
}
```

**Métriques exploitables dans Kibana:**
- Nombre de requêtes par endpoint
- Temps de réponse moyen/P95/P99
- Taux d'erreur (4xx/5xx)
- Répartition par client IP

---

### 1.2 Propager le Correlation ID

**Fichiers à modifier:**
1. `src/api/middleware.py` - Stocker correlation_id dans contextvars
2. `src/logging_config.py` - Inclure correlation_id automatiquement dans tous les logs
3. `src/modules/module3_orchestration/tasks.py` - Passer aux tâches Celery
4. `src/modules/module2_recommendation/cache.py` - Inclure dans operations Redis
5. `src/database/connection.py` - Inclure dans contexte SQLAlchemy

**Nouveau fichier:** `src/utils/context.py`
```python
from contextvars import ContextVar

correlation_id_var: ContextVar[str] = ContextVar('correlation_id', default=None)

def get_correlation_id() -> str:
    return correlation_id_var.get()

def set_correlation_id(correlation_id: str):
    correlation_id_var.set(correlation_id)
```

**Impact:**
- Traçabilité complète: API Request → Celery Task → Cache → Database → Vector Store
- Recherche dans Kibana par correlation_id pour voir toute la chaîne d'exécution
- Facilite le debugging des erreurs complexes

**Exemple de logs liés:**
```json
// Requête API
{"correlation_id": "abc123", "message": "Recommendation request", "client_id": "C1"}

// Tâche Celery lancée
{"correlation_id": "abc123", "message": "Starting async recommendation", "task_id": "xyz"}

// Recherche dans cache
{"correlation_id": "abc123", "message": "Cache miss", "key": "rec_C1_P1"}

// Query vector store
{"correlation_id": "abc123", "message": "Vector search", "collection": "vehicles", "duration_ms": 45}

// Réponse
{"correlation_id": "abc123", "message": "Request completed", "status": 200, "duration_seconds": 0.5}
```

---

### 1.3 Activer le Logging Database avec Métriques

**Fichier à modifier:** `src/database/connection.py`

**Objectif:** Logger toutes les queries SQL en production avec timing et détection des queries lentes.

**Actions:**
1. Créer event listener SQLAlchemy pour logger les queries
2. Logger queries lentes (> 100ms) avec niveau WARNING
3. Logger erreurs de pool de connexions
4. Logger métriques de pool (size, overflow, checked_out)

**Nouveau code:**
```python
from sqlalchemy import event
from sqlalchemy.engine import Engine
import time
import logging

logger = logging.getLogger(__name__)

@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    conn.info.setdefault('query_start_time', []).append(time.time())
    logger.debug(
        "Query execution started",
        extra={
            "query": statement[:200],  # Truncate long queries
            "parameters": str(parameters)[:100]
        }
    )

@event.listens_for(Engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    total_time = time.time() - conn.info['query_start_time'].pop()
    duration_ms = total_time * 1000

    log_level = "WARNING" if duration_ms > 100 else "INFO"
    logger.log(
        logging.WARNING if duration_ms > 100 else logging.INFO,
        f"Query executed in {duration_ms:.2f}ms",
        extra={
            "query": statement[:200],
            "duration_ms": duration_ms,
            "is_slow_query": duration_ms > 100,
            "query_type": statement.split()[0].upper()  # SELECT, INSERT, UPDATE, DELETE
        }
    )

# Logger pool stats périodiquement
async def log_pool_stats():
    pool = async_engine.pool
    logger.info(
        "Database pool statistics",
        extra={
            "pool_size": pool.size(),
            "checked_out_connections": pool.checkedout(),
            "overflow": pool.overflow(),
            "pool_timeout": pool._timeout
        }
    )
```

**Métriques dans Kibana:**
- Queries lentes (> 100ms)
- Répartition par type de query (SELECT/INSERT/UPDATE/DELETE)
- Pool de connexions utilization
- Erreurs de connexion

---

## 🚀 PHASE 2 - MÉTRIQUES APPLICATIVES (Priorité HAUTE)

### 2.1 Structured Logging pour Métriques

**Principe:** Utiliser structured logging avec des champs métriques standardisés que Kibana peut agréger.

**Format standard pour métriques:**
```json
{
  "timestamp": 1234567890.123,
  "level": "INFO",
  "logger": "metrics.cache",
  "service": "Sentiment Recommendation System",
  "message": "Cache operation completed",
  "metric_type": "cache_operation",
  "operation": "get",
  "cache_hit": true,
  "duration_ms": 15.5,
  "cache_key": "rec_C1_P1"
}
```

**Fichiers à modifier:**

#### A. Cache Metrics (`src/modules/module2_recommendation/cache.py`)

**Ajouter après chaque opération:**
```python
logger.info(
    "Cache operation completed",
    extra={
        "metric_type": "cache_operation",
        "operation": "get",  # get/set/delete
        "cache_hit": result is not None,
        "duration_ms": (time.time() - start) * 1000,
        "cache_key": key,
        "correlation_id": get_correlation_id()
    }
)
```

**Métriques Kibana:**
- Cache hit rate: `cache_hit:true / total cache_operation`
- Cache latency: avg/P95/P99 of `duration_ms`
- Operations par seconde

#### B. Vector Store Metrics (`src/modules/module2_recommendation/vector_store.py`)

```python
logger.info(
    "Vector search completed",
    extra={
        "metric_type": "vector_search",
        "collection": collection_name,
        "query_limit": limit,
        "results_count": len(results),
        "duration_ms": (time.time() - start) * 1000,
        "score_threshold": score_threshold,
        "correlation_id": get_correlation_id()
    }
)
```

**Métriques Kibana:**
- Search latency par collection
- Nombre de résultats retournés
- Performance des différents types de recherche

#### C. ML Model Inference Metrics

**Sentiment Analysis (`src/modules/module1_sentiment/analyzer.py`):**
```python
logger.info(
    "Sentiment analysis completed",
    extra={
        "metric_type": "ml_inference",
        "model": "sentiment_analyzer",
        "text_length": len(text),
        "sentiment": result.sentiment,
        "confidence": result.confidence,
        "duration_ms": (time.time() - start) * 1000,
        "correlation_id": get_correlation_id()
    }
)
```

**Embeddings (`src/modules/module2_recommendation/embeddings.py`):**
```python
logger.info(
    "Embedding generation completed",
    extra={
        "metric_type": "ml_inference",
        "model": "sentence_transformer",
        "batch_size": len(texts),
        "duration_ms": (time.time() - start) * 1000,
        "avg_text_length": sum(len(t) for t in texts) / len(texts),
        "correlation_id": get_correlation_id()
    }
)
```

**Métriques Kibana:**
- Inference time par modèle
- Distribution des scores de confiance
- Throughput (textes/sec)

#### D. Celery Task Metrics (`src/modules/module3_orchestration/tasks.py`)

```python
logger.info(
    "Celery task completed",
    extra={
        "metric_type": "celery_task",
        "task_name": self.name,
        "task_id": task_id,
        "status": "success",  # success/failure/retry
        "duration_ms": (time.time() - start) * 1000,
        "retry_count": self.request.retries,
        "correlation_id": kwargs.get('correlation_id')
    }
)
```

**Métriques Kibana:**
- Task success rate par type
- Task duration par type
- Retry rate

---

### 2.2 Configurer Index Templates pour Métriques

**Nouveau fichier:** `monitoring/elasticsearch/index-templates/metrics-template.json`

```json
{
  "index_patterns": ["recommendation-metrics-*"],
  "template": {
    "settings": {
      "number_of_shards": 1,
      "number_of_replicas": 1,
      "index.refresh_interval": "5s"
    },
    "mappings": {
      "properties": {
        "timestamp": {"type": "date"},
        "metric_type": {"type": "keyword"},
        "duration_ms": {"type": "float"},
        "cache_hit": {"type": "boolean"},
        "correlation_id": {"type": "keyword"},
        "service": {"type": "keyword"},
        "operation": {"type": "keyword"}
      }
    }
  }
}
```

**Impact:** Optimisation des requêtes Kibana pour les métriques.

---

## 🚀 PHASE 3 - CUSTOM APM SPANS (Priorité HAUTE)

### 3.1 Instrumenter les Opérations Critiques

**Objectif:** Ajouter des spans APM personnalisés pour voir la timeline détaillée des opérations dans Kibana APM UI.

**Import nécessaire:**
```python
import elasticapm
from elasticapm import capture_span, label, set_custom_context
```

#### A. Sentiment Analysis

**Fichier:** `src/modules/module1_sentiment/analyzer.py`

```python
@capture_span(span_type='ml.inference', span_subtype='sentiment')
async def analyze_sentiment(self, text: str) -> SentimentResult:
    """Analyze sentiment with APM tracing."""

    # Add labels for filtering in APM
    elasticapm.label(
        text_length=len(text),
        model="distilcamembert"
    )

    try:
        result = await self._run_inference(text)

        # Add result metadata
        elasticapm.label(
            sentiment=result.sentiment,
            confidence=result.confidence
        )

        return result
    except Exception as e:
        elasticapm.capture_exception()
        raise
```

#### B. Vector Search

**Fichier:** `src/modules/module2_recommendation/vector_store.py`

```python
@capture_span(span_type='db.qdrant', span_subtype='search')
async def search(self, collection: str, vector: List[float], limit: int):
    """Search with APM tracing."""

    elasticapm.label(
        collection=collection,
        limit=limit,
        vector_dim=len(vector)
    )

    with elasticapm.capture_span("qdrant.search_query", span_type="db.qdrant"):
        results = await self.client.search(
            collection_name=collection,
            query_vector=vector,
            limit=limit
        )

    elasticapm.label(results_count=len(results))
    return results
```

#### C. Cache Operations

**Fichier:** `src/modules/module2_recommendation/cache.py`

```python
@capture_span(span_type='cache.redis', span_subtype='get')
async def get_cached_result(self, key: str):
    """Get from cache with APM tracing."""

    elasticapm.label(cache_key=key)

    result = await self.redis.get(key)

    elasticapm.label(cache_hit=result is not None)
    return result
```

#### D. Database Queries

**Fichier:** `src/database/repositories.py`

```python
@capture_span(span_type='db.postgresql', span_subtype='query')
async def get_vehicle_by_id(self, vehicle_id: str):
    """Get vehicle with APM tracing."""

    elasticapm.label(
        query_type="select",
        table="vehicles",
        vehicle_id=vehicle_id
    )

    result = await self.session.execute(...)
    return result
```

#### E. Complete Workflow

**Fichier:** `src/modules/module3_orchestration/orchestrator.py`

```python
@capture_span(span_type='app.workflow', span_subtype='recommendation')
async def process_recommendation_request(self, ...):
    """Complete recommendation workflow with APM tracing."""

    # Set custom context for the entire transaction
    elasticapm.set_custom_context({
        "product_id": product_id,
        "client_id": client_id,
        "product_type": product_type
    })

    # Phase 1: Sentiment Analysis (auto-traced by decorator)
    with elasticapm.capture_span("workflow.sentiment_analysis"):
        sentiment_result = await self.sentiment_analyzer.analyze(comment)

    # Phase 2: Recommendation (auto-traced)
    with elasticapm.capture_span("workflow.generate_recommendations"):
        recommendations = await self.recommendation_engine.get_recommendations(...)

    # Phase 3: Ranking (auto-traced)
    with elasticapm.capture_span("workflow.rank_results"):
        ranked = await self.ranker.rank(recommendations, sentiment_result)

    return ranked
```

**Impact dans Kibana APM:**
```
Transaction: POST /api/v1/recommendations (500ms)
├─ workflow.sentiment_analysis (150ms)
│  └─ ml.inference.sentiment (145ms)
├─ workflow.generate_recommendations (300ms)
│  ├─ cache.redis.get (10ms) [cache_hit: false]
│  ├─ ml.inference.embeddings (80ms)
│  ├─ db.qdrant.search (200ms)
│  └─ cache.redis.set (10ms)
└─ workflow.rank_results (50ms)
   └─ db.postgresql.query (45ms)
```

---

## 🚀 PHASE 4 - MONITORING SERVICES EXTERNES (Priorité MOYENNE)

### 4.1 Metricbeat pour Services Infrastructure

**Nouveau fichier:** `monitoring/metricbeat/metricbeat.yml`

```yaml
metricbeat.modules:
  # Redis monitoring
  - module: redis
    metricsets: ["info", "keyspace"]
    period: 10s
    hosts: ["redis:6379"]

  # PostgreSQL monitoring
  - module: postgresql
    metricsets: ["database", "bgwriter", "activity"]
    period: 10s
    hosts: ["postgres://postgres:5432?sslmode=disable"]
    username: ${POSTGRES_USER}
    password: ${POSTGRES_PASSWORD}

  # Docker monitoring
  - module: docker
    metricsets: ["container", "cpu", "memory", "network"]
    period: 10s
    hosts: ["unix:///var/run/docker.sock"]

output.elasticsearch:
  hosts: ["http://elasticsearch:9200"]
  index: "metricbeat-%{+yyyy.MM.dd}"
```

**Ajouter dans docker-compose.yml:**
```yaml
metricbeat:
  image: docker.elastic.co/beats/metricbeat:8.11.0
  user: root
  volumes:
    - ./monitoring/metricbeat/metricbeat.yml:/usr/share/metricbeat/metricbeat.yml:ro
    - /var/run/docker.sock:/var/run/docker.sock:ro
    - /sys/fs/cgroup:/hostfs/sys/fs/cgroup:ro
    - /proc:/hostfs/proc:ro
    - /:/hostfs:ro
  environment:
    - POSTGRES_USER=${POSTGRES_USER}
    - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
  depends_on:
    - elasticsearch
    - redis
    - postgres
  networks:
    - recommendation-network
```

**Métriques collectées:**
- Redis: memory usage, commands/sec, hit rate, keyspace
- PostgreSQL: connections, transactions/sec, locks, cache hit ratio
- Docker: CPU/Memory per container, network I/O

---

### 4.2 Health Checks avec Métriques Enrichies

**Fichier à modifier:** `src/api/routes/health.py`

**Ajouter des métriques détaillées:**
```python
@router.get("/detailed")
async def detailed_health_check():
    """Health check with detailed metrics."""

    health_data = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {},
        "metrics": {}
    }

    # Redis metrics
    try:
        cache = get_cache_manager()
        redis_info = await cache.redis.info()
        health_data["services"]["redis"] = {
            "status": "healthy",
            "used_memory_mb": redis_info["used_memory"] / 1024 / 1024,
            "connected_clients": redis_info["connected_clients"],
            "total_commands_processed": redis_info["total_commands_processed"],
            "hit_rate": redis_info.get("keyspace_hits", 0) /
                       (redis_info.get("keyspace_hits", 0) + redis_info.get("keyspace_misses", 1))
        }
    except Exception as e:
        health_data["services"]["redis"] = {"status": "unhealthy", "error": str(e)}

    # Qdrant metrics
    try:
        vector_store = get_vector_store()
        collections = await vector_store.list_collections()
        health_data["services"]["qdrant"] = {
            "status": "healthy",
            "collections_count": len(collections),
            "collections": [
                {
                    "name": col.name,
                    "vectors_count": col.vectors_count,
                    "points_count": col.points_count
                }
                for col in collections
            ]
        }
    except Exception as e:
        health_data["services"]["qdrant"] = {"status": "unhealthy", "error": str(e)}

    # Database metrics
    try:
        pool = async_engine.pool
        health_data["services"]["database"] = {
            "status": "healthy",
            "pool_size": pool.size(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow()
        }
    except Exception as e:
        health_data["services"]["database"] = {"status": "unhealthy", "error": str(e)}

    # Log the health check
    logger.info(
        "Health check performed",
        extra={
            "metric_type": "health_check",
            "overall_status": health_data["status"],
            "services_healthy": sum(1 for s in health_data["services"].values() if s.get("status") == "healthy"),
            "services_total": len(health_data["services"])
        }
    )

    return health_data
```

---

## 🚀 PHASE 5 - KIBANA ALERTING & DASHBOARDS (Priorité MOYENNE)

### 5.1 Kibana Watcher Rules

**Nouveau répertoire:** `monitoring/kibana/rules/`

#### Alert 1: High Error Rate

**Fichier:** `monitoring/kibana/rules/high-error-rate.json`

```json
{
  "name": "High Error Rate Alert",
  "schedule": {
    "interval": "5m"
  },
  "trigger": {
    "condition": {
      "compare": {
        "ctx.payload.hits.total": {
          "gt": 10
        }
      }
    }
  },
  "input": {
    "search": {
      "request": {
        "indices": ["recommendation-*-logs-*"],
        "body": {
          "query": {
            "bool": {
              "must": [
                {
                  "range": {
                    "timestamp": {
                      "gte": "now-5m"
                    }
                  }
                },
                {
                  "term": {
                    "level": "ERROR"
                  }
                }
              ]
            }
          }
        }
      }
    }
  },
  "actions": {
    "log_action": {
      "logging": {
        "text": "High error rate detected: {{ctx.payload.hits.total}} errors in last 5 minutes"
      }
    }
  }
}
```

#### Alert 2: Slow API Response

**Fichier:** `monitoring/kibana/rules/slow-api-response.json`

```json
{
  "name": "Slow API Response Alert",
  "schedule": {
    "interval": "5m"
  },
  "trigger": {
    "condition": {
      "compare": {
        "ctx.payload.aggregations.avg_duration.value": {
          "gt": 2000
        }
      }
    }
  },
  "input": {
    "search": {
      "request": {
        "indices": ["recommendation-api-logs-*"],
        "body": {
          "query": {
            "range": {
              "timestamp": {
                "gte": "now-5m"
              }
            }
          },
          "aggs": {
            "avg_duration": {
              "avg": {
                "field": "duration_ms"
              }
            },
            "p95_duration": {
              "percentiles": {
                "field": "duration_ms",
                "percents": [95]
              }
            }
          }
        }
      }
    }
  },
  "actions": {
    "log_action": {
      "logging": {
        "text": "Slow API detected: Avg={{ctx.payload.aggregations.avg_duration.value}}ms, P95={{ctx.payload.aggregations.p95_duration.values.95.0}}ms"
      }
    }
  }
}
```

#### Alert 3: Cache Performance Degradation

**Fichier:** `monitoring/kibana/rules/cache-low-hit-rate.json`

```json
{
  "name": "Cache Low Hit Rate Alert",
  "schedule": {
    "interval": "10m"
  },
  "trigger": {
    "condition": {
      "script": {
        "source": "ctx.payload.aggregations.hit_rate.value < 0.7",
        "lang": "painless"
      }
    }
  },
  "input": {
    "search": {
      "request": {
        "indices": ["recommendation-*-logs-*"],
        "body": {
          "query": {
            "bool": {
              "must": [
                {
                  "range": {
                    "timestamp": {
                      "gte": "now-10m"
                    }
                  }
                },
                {
                  "term": {
                    "metric_type": "cache_operation"
                  }
                }
              ]
            }
          },
          "aggs": {
            "hit_rate": {
              "avg": {
                "field": "cache_hit"
              }
            }
          }
        }
      }
    }
  }
}
```

#### Alert 4: Database Connection Pool Exhaustion

**Fichier:** `monitoring/kibana/rules/db-pool-exhaustion.json`

```json
{
  "name": "Database Pool Exhaustion Alert",
  "schedule": {
    "interval": "2m"
  },
  "trigger": {
    "condition": {
      "compare": {
        "ctx.payload.hits.hits.0._source.checked_out_connections": {
          "gte": 25
        }
      }
    }
  },
  "input": {
    "search": {
      "request": {
        "indices": ["recommendation-*-logs-*"],
        "body": {
          "query": {
            "bool": {
              "must": [
                {
                  "range": {
                    "timestamp": {
                      "gte": "now-2m"
                    }
                  }
                },
                {
                  "exists": {
                    "field": "pool_size"
                  }
                }
              ]
            }
          },
          "sort": [
            {
              "timestamp": "desc"
            }
          ],
          "size": 1
        }
      }
    }
  }
}
```

---

### 5.2 Nouveaux Dashboards Kibana

#### Dashboard 1: Application Metrics Dashboard

**Visualizations:**
1. **Cache Performance**
   - Hit Rate (line chart)
   - Operations per second (area chart)
   - Average latency (line chart)

2. **ML Model Performance**
   - Inference time distribution (histogram)
   - Sentiment confidence distribution (histogram)
   - Throughput (texts/sec)

3. **Database Performance**
   - Query latency P50/P95/P99 (line chart)
   - Slow queries count (metric)
   - Pool utilization (gauge)

4. **Vector Search Performance**
   - Search latency by collection (line chart)
   - Results count distribution (histogram)
   - Operations per second (metric)

#### Dashboard 2: Business Metrics Dashboard

**Visualizations:**
1. **Recommendation Quality**
   - Average similarity scores (line chart)
   - Recommendations per request (histogram)
   - Sentiment distribution (pie chart)

2. **API Usage**
   - Requests per endpoint (bar chart)
   - Response time by endpoint (heat map)
   - Error rate by endpoint (line chart)

3. **Celery Tasks**
   - Task success rate (gauge)
   - Task duration by type (box plot)
   - Queue depth over time (area chart)

#### Dashboard 3: Infrastructure Health

**Visualizations:**
1. **Redis Metrics** (from Metricbeat)
   - Memory usage (line chart)
   - Commands per second (line chart)
   - Connected clients (metric)

2. **PostgreSQL Metrics** (from Metricbeat)
   - Active connections (line chart)
   - Transactions per second (line chart)
   - Cache hit ratio (gauge)

3. **Docker Containers**
   - CPU usage per container (stacked area)
   - Memory usage per container (stacked area)
   - Network I/O (line chart)

---

## 🚀 PHASE 6 - LOGGING ENRICHI (Priorité BASSE)

### 6.1 Contexte Utilisateur dans Logs

**Fichier:** `src/api/middleware.py`

**Ajouter extraction des informations utilisateur:**
```python
class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Extract user context
        user_id = request.headers.get("X-User-ID")
        session_id = request.headers.get("X-Session-ID")
        client_type = request.headers.get("X-Client-Type", "web")

        # Add to context
        extra_context = {
            "user_id": user_id,
            "session_id": session_id,
            "client_type": client_type,
            "user_agent": request.headers.get("User-Agent"),
            "referer": request.headers.get("Referer")
        }

        # Log request with context
        logger.info(
            "Incoming request",
            extra={
                **extra_context,
                "method": request.method,
                "path": request.url.path,
                "correlation_id": get_correlation_id()
            }
        )

        # ... rest of middleware
```

### 6.2 Sanitization des Données Sensibles

**Fichier:** `src/logging_config.py`

**Ajouter filtre de sanitization:**
```python
class SanitizingFilter(logging.Filter):
    """Remove sensitive data from logs."""

    SENSITIVE_FIELDS = [
        "password", "token", "api_key", "secret",
        "credit_card", "ssn", "authorization"
    ]

    def filter(self, record):
        if hasattr(record, 'args') and isinstance(record.args, dict):
            for field in self.SENSITIVE_FIELDS:
                if field in record.args:
                    record.args[field] = "***REDACTED***"

        # Sanitize message
        message = record.getMessage()
        for field in self.SENSITIVE_FIELDS:
            if field in message.lower():
                record.msg = re.sub(
                    rf'{field}[=:]\s*\S+',
                    f'{field}=***REDACTED***',
                    message,
                    flags=re.IGNORECASE
                )

        return True

# Add to all handlers
for handler in logging.root.handlers:
    handler.addFilter(SanitizingFilter())
```

---

## 📊 RÉCAPITULATIF DES MODIFICATIONS

### Fichiers à Modifier

| Phase | Fichier | Modifications |
|-------|---------|---------------|
| **1.1** | `src/api/app.py` | Enregistrer 2 middleware |
| **1.2** | `src/api/middleware.py` | Utiliser contextvars |
| **1.2** | `src/logging_config.py` | Auto-inclure correlation_id |
| **1.2** | `src/modules/module3_orchestration/tasks.py` | Passer correlation_id |
| **1.3** | `src/database/connection.py` | Event listeners SQL |
| **2.1** | `src/modules/module2_recommendation/cache.py` | Métriques structured logs |
| **2.1** | `src/modules/module2_recommendation/vector_store.py` | Métriques structured logs |
| **2.1** | `src/modules/module1_sentiment/analyzer.py` | Métriques structured logs |
| **2.1** | `src/modules/module2_recommendation/embeddings.py` | Métriques structured logs |
| **2.1** | `src/modules/module3_orchestration/celery_app.py` | Métriques structured logs |
| **3.1** | Tous les modules critiques | Ajouter APM spans |
| **4.2** | `src/api/routes/health.py` | Health check détaillé |

### Fichiers à Créer

| Phase | Fichier | Description |
|-------|---------|-------------|
| **1.2** | `src/utils/context.py` | Contextvars pour correlation_id |
| **2.2** | `monitoring/elasticsearch/index-templates/metrics-template.json` | Template index métriques |
| **4.1** | `monitoring/metricbeat/metricbeat.yml` | Config Metricbeat |
| **5.1** | `monitoring/kibana/rules/*.json` | 4+ règles d'alerting |
| **5.2** | `monitoring/kibana/dashboards/*.ndjson` | 3 nouveaux dashboards |

### Modifications Docker Compose

```yaml
# Ajouter service Metricbeat
metricbeat:
  image: docker.elastic.co/beats/metricbeat:8.11.0
  ...

# Modifier retention Elasticsearch (optionnel)
elasticsearch:
  environment:
    - "indices.lifecycle.history_index_enabled=true"
    - "xpack.monitoring.collection.enabled=true"
```

---

## ✅ VALIDATION & TESTS

### Checklist de Validation

**Phase 1:**
- [ ] Tous les logs HTTP contiennent `correlation_id`
- [ ] Correlation ID traverse Celery/Cache/Database
- [ ] Queries SQL loggées avec timing
- [ ] Queries lentes (>100ms) en WARNING

**Phase 2:**
- [ ] Cache hit/miss rate visible dans Kibana
- [ ] ML inference time visible dans Kibana
- [ ] Vector search latency visible dans Kibana
- [ ] Celery task metrics visible dans Kibana

**Phase 3:**
- [ ] APM spans visibles dans Kibana APM UI
- [ ] Timeline complète des opérations
- [ ] Labels APM exploitables (filtres)

**Phase 4:**
- [ ] Metricbeat collecte Redis metrics
- [ ] Metricbeat collecte PostgreSQL metrics
- [ ] Metricbeat collecte Docker metrics
- [ ] Health check détaillé fonctionnel

**Phase 5:**
- [ ] 4 règles d'alerting actives
- [ ] 3 nouveaux dashboards créés
- [ ] Dashboards affichent données en temps réel

---

## 🎯 RÉSULTAT FINAL

Après implémentation complète, nous aurons:

✅ **Logs Complets:**
- Toutes les requêtes HTTP loggées avec correlation_id
- Database queries loggées avec timing
- Cache operations avec hit/miss metrics
- ML inference avec timing et confidence

✅ **Métriques Infrastructure:**
- Redis: memory, commands/sec, hit rate
- PostgreSQL: connections, transactions, cache hit
- Docker: CPU/memory per container
- Collectées via Metricbeat

✅ **Métriques Applicatives:**
- Cache hit rate, latency
- Vector search performance
- ML model inference time
- Celery task success rate, queue depth
- Collectées via structured logging

✅ **Distributed Tracing:**
- APM spans pour toutes opérations critiques
- Timeline complète visible dans Kibana APM
- Labels pour filtrage et analyse

✅ **Alerting:**
- 4+ règles configurées
- Alertes sur: error rate, API latency, cache performance, DB pool

✅ **Dashboards:**
- 6 dashboards total (3 existants + 3 nouveaux)
- Application Metrics, Business Metrics, Infrastructure Health

✅ **Traçabilité:**
- Correlation ID à travers tout le système
- Recherche Kibana par correlation_id
- Debug facilité des problèmes complexes

---

## 🚀 ORDRE D'EXÉCUTION

**Aujourd'hui (2-3h):**
1. Phase 1.1 - Middleware (30min)
2. Phase 1.2 - Correlation ID (1h)
3. Phase 1.3 - Database logging (1h)
4. Test & Validation Phase 1

**Demain (3-4h):**
5. Phase 2 - Métriques applicatives (2h)
6. Phase 3 - APM spans (2h)
7. Test & Validation Phases 2-3

**Cette semaine (2h):**
8. Phase 4 - Metricbeat (1h)
9. Phase 5 - Alerting & Dashboards (1h)
10. Test & Validation complète

---

**Status:** ✅ Plan d'action finalisé - 100% ELK Stack, 0% Prometheus
