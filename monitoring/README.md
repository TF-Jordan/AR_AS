# Monitoring Stack - ELK + APM + Metricbeat

Complete monitoring solution using ELK Stack (Elasticsearch, Logstash, Kibana) + Elastic APM + Metricbeat.

## 📊 Architecture

```
Application Logs (JSON) → Filebeat → Logstash → Elasticsearch → Kibana
Infrastructure Metrics  → Metricbeat → Elasticsearch → Kibana
APM Traces             → APM Server → Elasticsearch → Kibana
```

## 🎯 What's Monitored

### Application Metrics (via Structured Logging)
- ✅ **HTTP Requests**: Method, path, status, duration_ms, correlation_id
- ✅ **Cache Operations**: hit/miss rate, latency, data size
- ✅ **Vector Search**: query latency, results count, similarity scores
- ✅ **ML Inference**: sentiment analysis timing, embedding generation
- ✅ **Database Queries**: query type, duration, slow query detection (>100ms)
- ✅ **Celery Tasks**: success/failure rate, retry count, duration

### Infrastructure Metrics (via Metricbeat)
- ✅ **Redis**: memory usage, commands/sec, keyspace stats
- ✅ **PostgreSQL**: connections, transactions/sec, cache hit ratio
- ✅ **Docker**: CPU/memory per container, network I/O
- ✅ **System**: CPU, memory, disk, network

### Distributed Tracing (via Elastic APM)
- ✅ **HTTP Transactions**: Complete request timeline
- ✅ **Exception Tracking**: Automatic error capture
- ✅ **Correlation ID**: End-to-end request tracing

## 🚀 Quick Start

### 1. Start Monitoring Stack

```bash
# Start all services (app + monitoring)
docker-compose up -d

# Check services health
docker-compose ps

# View logs
docker-compose logs -f
```

### 2. Access Dashboards

- **Kibana**: http://localhost:5601
- **Elasticsearch**: http://localhost:9200
- **APM**: http://localhost:5601/app/apm

### 3. Import Kibana Dashboards

```bash
# Option A: Utiliser le script automatique (recommandé)
./monitoring/kibana/setup-dashboards.sh

# Option B: Import manuel via l'API Kibana
curl -X POST "http://localhost:5601/api/saved_objects/_import?overwrite=true" \
  -u elastic:Ar@s_Elastic_2024! \
  -H "kbn-xsrf: true" \
  --form file=@monitoring/kibana/dashboards/api-logs-dashboard.ndjson

curl -X POST "http://localhost:5601/api/saved_objects/_import?overwrite=true" \
  -u elastic:Ar@s_Elastic_2024! \
  -H "kbn-xsrf: true" \
  --form file=@monitoring/kibana/dashboards/recommendation-dashboards.ndjson
```

## 📈 Key Metrics to Monitor

### Cache Performance
```
metric_type: cache_operation
Fields: cache_hit, cache_hit_type, duration_ms
```

**Kibana Query:**
```
event: cache_get AND metric_type: cache_operation
```

**Key Metrics:**
- Cache Hit Rate: `cache_hit:true / total cache operations`
- Average Latency: `avg(duration_ms)`

### API Performance
```
event: request_completed
Fields: method, path, status_code, duration_ms
```

**Kibana Query:**
```
event: request_completed AND path: "/api/v1/recommendations"
```

**Key Metrics:**
- P95 Response Time: `percentile(duration_ms, 95)`
- Error Rate: `status_code >= 400`

### Database Performance
```
metric_type: database_query
Fields: query_type, duration_ms, is_slow_query
```

**Kibana Query:**
```
metric_type: database_query AND is_slow_query: true
```

**Key Metrics:**
- Slow Queries: `is_slow_query:true`
- Queries by Type: `query_type: SELECT|INSERT|UPDATE|DELETE`

### ML Inference Performance
```
metric_type: ml_inference
Fields: model, operation, duration_ms, confidence
```

**Kibana Query:**
```
metric_type: ml_inference AND operation: sentiment_analysis
```

**Key Metrics:**
- Inference Time: `avg(duration_ms) by model`
- Confidence Distribution: `avg(confidence)`

## 🔍 Correlation ID Tracing

Every request gets a `correlation_id` that propagates through:
1. HTTP Request → API logs
2. Celery Task → Background job logs
3. Database Query → SQL logs
4. Cache Operation → Redis logs
5. Vector Search → Qdrant logs

**Search by Correlation ID:**
```
correlation_id: "550e8400-e29b-41d4-a716-446655440000"
```

This shows the complete execution chain!

## 🚨 Configured Alerts

### 1. High Error Rate
- **Trigger**: >10 errors in 5 minutes
- **File**: `monitoring/kibana/rules/high-error-rate.json`
- **Action**: Log alert message

### 2. Slow API Response
- **Trigger**: >5 requests with duration >2s in 5 minutes
- **File**: `monitoring/kibana/rules/slow-api-response.json`
- **Action**: Log warning

### 3. Cache Low Hit Rate
- **Trigger**: >100 cache misses in 10 minutes
- **File**: `monitoring/kibana/rules/cache-low-hit-rate.json`
- **Action**: Log warning

## 📊 Available Dashboards

### 1. API Logs Dashboard (NEW)
Dashboard complet pour la visualisation des logs API avec 15 panneaux :
- **KPI Metrics** : Total requêtes, taux d'erreurs (%), temps de réponse moyen, P95
- **Requêtes dans le temps** : Bar chart empilé succès/erreurs 4xx/erreurs 5xx
- **Temps de réponse** : Courbes moyenne, P95, P99 dans le temps
- **Distribution codes HTTP** : Donut chart des codes de statut
- **Catégories de réponse** : Pie chart fast/normal/slow/very_slow
- **Top 10 Endpoints** : Tableau avec requêtes, temps moyen, P95, erreurs
- **Requêtes par méthode HTTP** : GET, POST, PUT, DELETE dans le temps
- **Logs par service** : api, celery_worker, celery_beat, flower
- **Logs par niveau** : INFO, WARNING, ERROR, CRITICAL
- **Erreurs récentes** : Tableau des erreurs avec endpoint et status code
- **Requêtes lentes** : Tableau des requêtes >500ms avec détails
- **Correlation ID tracking** : Suivi bout-en-bout des requêtes

### 2. Recommendation System - Overview
- Logs by service
- Errors over time
- Response time distribution
- Top 10 endpoints

### 3. Application Metrics
- Cache hit/miss rate
- ML inference time
- Database query performance
- Vector search latency

### 4. Infrastructure Health
- Redis metrics (from Metricbeat)
- PostgreSQL metrics (from Metricbeat)
- Docker container metrics (from Metricbeat)

## 🔧 Configuration Files

```
monitoring/
├── filebeat/
│   └── filebeat.yml          # Log collection config
├── logstash/
│   ├── pipeline/
│   │   └── logstash.conf     # Log processing pipeline
│   └── config/
│       └── logstash.yml      # Logstash settings
├── metricbeat/
│   └── metricbeat.yml        # Infrastructure metrics config
└── kibana/
    ├── setup-dashboards.sh   # Script d'import automatique
    ├── dashboards/
    │   ├── api-logs-dashboard.ndjson          # Dashboard API Logs (15 panneaux)
    │   └── recommendation-dashboards.ndjson   # Dashboards overview
    └── rules/
        ├── high-error-rate.json
        ├── slow-api-response.json
        └── cache-low-hit-rate.json
```

## 🐛 Troubleshooting

### Check Elasticsearch Health
```bash
curl http://localhost:9200/_cluster/health?pretty
```

### View Metricbeat Logs
```bash
docker-compose logs metricbeat
```

### Test Logstash Pipeline
```bash
docker-compose exec logstash logstash -f /usr/share/logstash/pipeline/logstash.conf --config.test_and_exit
```

### Check Index Patterns
```bash
curl http://localhost:9200/_cat/indices?v
```

## 📖 Useful Kibana Queries

### Find All Slow Requests
```
is_slow_request: true
```

### Cache Performance by Type
```
metric_type: cache_operation
Group by: cache_hit_type.keyword
```

### Database Queries by Type
```
metric_type: database_query
Visualize: query_type.keyword
```

### ML Inference Time Trend
```
metric_type: ml_inference
Y-axis: avg(duration_ms)
X-axis: @timestamp
Split by: model.keyword
```

## 🎓 Best Practices

1. **Always use correlation_id** when debugging issues
2. **Set up alerting** for critical metrics (error rate, latency)
3. **Monitor cache hit rate** - should be >70%
4. **Watch for slow queries** - optimize queries >100ms
5. **Track ML inference time** - ensure consistent performance
6. **Monitor Celery queue depth** - detect bottlenecks early

## 📚 Documentation

- [Elastic Stack Guide](https://www.elastic.co/guide/index.html)
- [Filebeat Reference](https://www.elastic.co/guide/en/beats/filebeat/current/index.html)
- [Metricbeat Reference](https://www.elastic.co/guide/en/beats/metricbeat/current/index.html)
- [Elastic APM](https://www.elastic.co/guide/en/apm/guide/current/index.html)
- [Kibana Query Language](https://www.elastic.co/guide/en/kibana/current/kuery-query.html)
