#!/bin/bash
# =============================================================================
# Script de création du Dashboard API Logs pour Kibana 8.11
# =============================================================================
# Crée via l'API Kibana :
#   1. Les data views (index patterns)
#   2. Les visualisations Lens (une par une)
#   3. Le dashboard complet avec 15 panneaux
#
# Usage:
#   ./setup-dashboards.sh
#   KIBANA_URL=http://localhost:5601 ELASTIC_PASSWORD=mypass ./setup-dashboards.sh
# =============================================================================

set -euo pipefail

KIBANA_URL="${KIBANA_URL:-http://localhost:5601}"
ELASTIC_USER="${ELASTIC_USER:-elastic}"
ELASTIC_PASSWORD="${ELASTIC_PASSWORD:-Ar@s_Elastic_2024!}"
ELASTICSEARCH_URL="${ELASTICSEARCH_URL:-http://localhost:9200}"
MAX_RETRIES=30
RETRY_INTERVAL=10

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1"; }

AUTH="${ELASTIC_USER}:${ELASTIC_PASSWORD}"

# =============================================================================
# Helper: Create or update a saved object via Kibana API
# =============================================================================
create_saved_object() {
    local obj_type="$1"
    local obj_id="$2"
    local body="$3"
    local title="$4"

    # Try to create
    local response
    response=$(curl -s -w "\n%{http_code}" -X POST \
        -u "$AUTH" \
        -H "kbn-xsrf: true" \
        -H "Content-Type: application/json" \
        "${KIBANA_URL}/api/saved_objects/${obj_type}/${obj_id}?overwrite=true" \
        -d "$body" 2>&1)

    local http_code
    http_code=$(echo "$response" | tail -1)
    local body_response
    body_response=$(echo "$response" | head -n -1)

    if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
        log_success "  ${title}"
        return 0
    elif echo "$body_response" | grep -q "Conflict"; then
        # Update existing
        curl -sf -X PUT \
            -u "$AUTH" \
            -H "kbn-xsrf: true" \
            -H "Content-Type: application/json" \
            "${KIBANA_URL}/api/saved_objects/${obj_type}/${obj_id}" \
            -d "$body" > /dev/null 2>&1
        log_success "  ${title} (mis à jour)"
        return 0
    else
        log_warn "  ${title} - HTTP ${http_code}: $(echo "$body_response" | head -c 150)"
        return 1
    fi
}

# =============================================================================
# Wait for services
# =============================================================================
wait_for_elasticsearch() {
    log_info "Attente d'Elasticsearch..."
    local retries=0
    while [ $retries -lt $MAX_RETRIES ]; do
        if curl -sf -u "$AUTH" "${ELASTICSEARCH_URL}/_cluster/health" > /dev/null 2>&1; then
            log_success "Elasticsearch est prêt!"; return 0
        fi
        retries=$((retries + 1)); sleep $RETRY_INTERVAL
    done
    log_error "Elasticsearch non disponible"; exit 1
}

wait_for_kibana() {
    log_info "Attente de Kibana..."
    local retries=0
    while [ $retries -lt $MAX_RETRIES ]; do
        if curl -sf -u "$AUTH" "${KIBANA_URL}/api/status" > /dev/null 2>&1; then
            log_success "Kibana est prêt!"; return 0
        fi
        retries=$((retries + 1)); sleep $RETRY_INTERVAL
    done
    log_error "Kibana non disponible"; exit 1
}

# =============================================================================
# Create Elasticsearch index template
# =============================================================================
create_index_template() {
    log_info "Création du template d'index..."
    curl -sf -X PUT -u "$AUTH" -H "Content-Type: application/json" \
        "${ELASTICSEARCH_URL}/_index_template/recommendation-logs" \
        -d '{
            "index_patterns": ["recommendation-*-logs-*"],
            "template": {
                "settings": { "number_of_shards": 1, "number_of_replicas": 0 },
                "mappings": {
                    "properties": {
                        "@timestamp": { "type": "date" },
                        "level": { "type": "keyword" },
                        "logger": { "type": "keyword" },
                        "log_message": { "type": "text", "fields": { "keyword": { "type": "keyword" } } },
                        "service": { "type": "keyword" },
                        "service_type": { "type": "keyword" },
                        "container_name": { "type": "keyword" },
                        "request_id": { "type": "keyword" },
                        "correlation_id": { "type": "keyword" },
                        "user_id": { "type": "keyword" },
                        "session_id": { "type": "keyword" },
                        "http_method": { "type": "keyword" },
                        "request_path": { "type": "keyword" },
                        "http_status": { "type": "integer" },
                        "duration_ms": { "type": "float" },
                        "duration_seconds": { "type": "float" },
                        "client_ip": { "type": "ip", "ignore_malformed": true },
                        "user_agent": { "type": "text", "fields": { "keyword": { "type": "keyword" } } },
                        "response_category": { "type": "keyword" },
                        "is_slow_request": { "type": "boolean" },
                        "is_error": { "type": "boolean" },
                        "is_server_error": { "type": "boolean" }
                    }
                }
            },
            "priority": 200
        }' > /dev/null 2>&1 && log_success "Template créé" || log_warn "Template existe déjà"
}

# =============================================================================
# Create Data Views
# =============================================================================
create_data_views() {
    log_info "Création des data views..."

    for dv_data in \
        'all-logs-index-pattern|recommendation-*-logs-*|Recommendation - All Logs' \
        'api-logs-index-pattern|recommendation-api-logs-*|Recommendation - API Logs' \
        'error-logs-index-pattern|recommendation-errors-*|Recommendation - Error Logs' \
        'metricbeat-index-pattern|metricbeat-*|Metricbeat'; do

        IFS='|' read -r dv_id dv_title dv_name <<< "$dv_data"
        local result
        result=$(curl -sf -X POST -u "$AUTH" \
            -H "kbn-xsrf: true" -H "Content-Type: application/json" \
            "${KIBANA_URL}/api/data_views/data_view" \
            -d "{\"data_view\":{\"id\":\"${dv_id}\",\"title\":\"${dv_title}\",\"timeFieldName\":\"@timestamp\",\"name\":\"${dv_name}\"},\"override\":true}" 2>&1) \
            && log_success "  ${dv_name}" || log_warn "  ${dv_name}: erreur"
    done

    curl -sf -X POST -u "$AUTH" \
        -H "kbn-xsrf: true" -H "Content-Type: application/json" \
        "${KIBANA_URL}/api/data_views/default" \
        -d '{"data_view_id":"all-logs-index-pattern","force":true}' > /dev/null 2>&1
}

# =============================================================================
# Create Lens visualizations via individual API calls
# =============================================================================
create_visualizations() {
    log_info "Création des visualisations Lens..."

    # --- 1. Total Requêtes API ---
    create_saved_object "lens" "api-logs-total-requests" '{
        "attributes": {
            "title": "Total Requêtes API",
            "visualizationType": "lnsMetric",
            "state": "{\"datasourceStates\":{\"formBased\":{\"layers\":{\"layer1\":{\"columns\":{\"col1\":{\"label\":\"Total Requêtes\",\"dataType\":\"number\",\"operationType\":\"count\",\"isBucketed\":false,\"scale\":\"ratio\",\"sourceField\":\"___records___\"}},\"columnOrder\":[\"col1\"],\"incompleteColumns\":{}}}}},\"visualization\":{\"layerId\":\"layer1\",\"accessor\":\"col1\",\"layerType\":\"data\",\"subtitle\":\"Dernières 24h\"},\"query\":{\"query\":\"service_type: api\",\"language\":\"kuery\"},\"filters\":[],\"datasourceMetaData\":{\"filterableIndexPatterns\":[{\"id\":\"all-logs-index-pattern\",\"title\":\"recommendation-*-logs-*\"}]},\"references\":[{\"type\":\"index-pattern\",\"id\":\"all-logs-index-pattern\",\"name\":\"indexpattern-datasource-layer-layer1\"}]}",
            "description": "Nombre total de requêtes API"
        },
        "references": [{"type":"index-pattern","id":"all-logs-index-pattern","name":"indexpattern-datasource-layer-layer1"}]
    }' "Total Requêtes API"

    # --- 2. Taux d'Erreurs ---
    create_saved_object "lens" "api-logs-error-rate" '{
        "attributes": {
            "title": "Taux d Erreurs API",
            "visualizationType": "lnsMetric",
            "state": "{\"datasourceStates\":{\"formBased\":{\"layers\":{\"layer1\":{\"columns\":{\"col1\":{\"label\":\"Erreurs\",\"dataType\":\"number\",\"operationType\":\"count\",\"isBucketed\":false,\"scale\":\"ratio\",\"sourceField\":\"___records___\"}},\"columnOrder\":[\"col1\"],\"incompleteColumns\":{}}}}},\"visualization\":{\"layerId\":\"layer1\",\"accessor\":\"col1\",\"layerType\":\"data\",\"subtitle\":\"4xx + 5xx\"},\"query\":{\"query\":\"http_status >= 400\",\"language\":\"kuery\"},\"filters\":[],\"datasourceMetaData\":{\"filterableIndexPatterns\":[{\"id\":\"all-logs-index-pattern\",\"title\":\"recommendation-*-logs-*\"}]},\"references\":[{\"type\":\"index-pattern\",\"id\":\"all-logs-index-pattern\",\"name\":\"indexpattern-datasource-layer-layer1\"}]}",
            "description": "Nombre de requêtes en erreur (4xx + 5xx)"
        },
        "references": [{"type":"index-pattern","id":"all-logs-index-pattern","name":"indexpattern-datasource-layer-layer1"}]
    }' "Taux d'Erreurs API"

    # --- 3. Temps de Réponse Moyen ---
    create_saved_object "lens" "api-logs-avg-response-time" '{
        "attributes": {
            "title": "Temps de Réponse Moyen",
            "visualizationType": "lnsMetric",
            "state": "{\"datasourceStates\":{\"formBased\":{\"layers\":{\"layer1\":{\"columns\":{\"col1\":{\"label\":\"Temps Moyen (ms)\",\"dataType\":\"number\",\"operationType\":\"average\",\"isBucketed\":false,\"scale\":\"ratio\",\"sourceField\":\"duration_ms\"}},\"columnOrder\":[\"col1\"],\"incompleteColumns\":{}}}}},\"visualization\":{\"layerId\":\"layer1\",\"accessor\":\"col1\",\"layerType\":\"data\",\"subtitle\":\"Moyenne\"},\"query\":{\"query\":\"service_type: api\",\"language\":\"kuery\"},\"filters\":[],\"datasourceMetaData\":{\"filterableIndexPatterns\":[{\"id\":\"all-logs-index-pattern\",\"title\":\"recommendation-*-logs-*\"}]},\"references\":[{\"type\":\"index-pattern\",\"id\":\"all-logs-index-pattern\",\"name\":\"indexpattern-datasource-layer-layer1\"}]}",
            "description": "Temps de réponse moyen en ms"
        },
        "references": [{"type":"index-pattern","id":"all-logs-index-pattern","name":"indexpattern-datasource-layer-layer1"}]
    }' "Temps de Réponse Moyen"

    # --- 4. P95 Response Time ---
    create_saved_object "lens" "api-logs-p95-response-time" '{
        "attributes": {
            "title": "Temps de Réponse P95",
            "visualizationType": "lnsMetric",
            "state": "{\"datasourceStates\":{\"formBased\":{\"layers\":{\"layer1\":{\"columns\":{\"col1\":{\"label\":\"P95 (ms)\",\"dataType\":\"number\",\"operationType\":\"percentile\",\"isBucketed\":false,\"scale\":\"ratio\",\"sourceField\":\"duration_ms\",\"params\":{\"percentile\":95}}},\"columnOrder\":[\"col1\"],\"incompleteColumns\":{}}}}},\"visualization\":{\"layerId\":\"layer1\",\"accessor\":\"col1\",\"layerType\":\"data\",\"subtitle\":\"Percentile 95\"},\"query\":{\"query\":\"service_type: api\",\"language\":\"kuery\"},\"filters\":[],\"datasourceMetaData\":{\"filterableIndexPatterns\":[{\"id\":\"all-logs-index-pattern\",\"title\":\"recommendation-*-logs-*\"}]},\"references\":[{\"type\":\"index-pattern\",\"id\":\"all-logs-index-pattern\",\"name\":\"indexpattern-datasource-layer-layer1\"}]}",
            "description": "95ème percentile du temps de réponse"
        },
        "references": [{"type":"index-pattern","id":"all-logs-index-pattern","name":"indexpattern-datasource-layer-layer1"}]
    }' "Temps de Réponse P95"

    # --- 5. Requêtes dans le Temps ---
    create_saved_object "lens" "api-logs-requests-over-time" '{
        "attributes": {
            "title": "Requêtes API dans le Temps",
            "visualizationType": "lnsXY",
            "state": "{\"datasourceStates\":{\"formBased\":{\"layers\":{\"layer1\":{\"columns\":{\"col1\":{\"label\":\"Timestamp\",\"dataType\":\"date\",\"operationType\":\"date_histogram\",\"isBucketed\":true,\"scale\":\"interval\",\"sourceField\":\"@timestamp\",\"params\":{\"interval\":\"auto\"}},\"col2\":{\"label\":\"Requêtes\",\"dataType\":\"number\",\"operationType\":\"count\",\"isBucketed\":false,\"scale\":\"ratio\",\"sourceField\":\"___records___\"}},\"columnOrder\":[\"col1\",\"col2\"],\"incompleteColumns\":{}}}}},\"visualization\":{\"legend\":{\"isVisible\":true,\"position\":\"bottom\"},\"preferredSeriesType\":\"bar\",\"layers\":[{\"layerId\":\"layer1\",\"accessors\":[\"col2\"],\"seriesType\":\"bar\",\"layerType\":\"data\",\"xAccessor\":\"col1\"}],\"yTitle\":\"Requêtes\",\"xTitle\":\"Temps\"},\"query\":{\"query\":\"service_type: api\",\"language\":\"kuery\"},\"filters\":[],\"datasourceMetaData\":{\"filterableIndexPatterns\":[{\"id\":\"all-logs-index-pattern\",\"title\":\"recommendation-*-logs-*\"}]},\"references\":[{\"type\":\"index-pattern\",\"id\":\"all-logs-index-pattern\",\"name\":\"indexpattern-datasource-layer-layer1\"}]}",
            "description": "Volume de requêtes API dans le temps"
        },
        "references": [{"type":"index-pattern","id":"all-logs-index-pattern","name":"indexpattern-datasource-layer-layer1"}]
    }' "Requêtes API dans le Temps"

    # --- 6. Temps de Réponse dans le Temps ---
    create_saved_object "lens" "api-logs-response-time-over-time" '{
        "attributes": {
            "title": "Temps de Réponse dans le Temps",
            "visualizationType": "lnsXY",
            "state": "{\"datasourceStates\":{\"formBased\":{\"layers\":{\"layer1\":{\"columns\":{\"col1\":{\"label\":\"Timestamp\",\"dataType\":\"date\",\"operationType\":\"date_histogram\",\"isBucketed\":true,\"scale\":\"interval\",\"sourceField\":\"@timestamp\",\"params\":{\"interval\":\"auto\"}},\"col2\":{\"label\":\"Moyenne (ms)\",\"dataType\":\"number\",\"operationType\":\"average\",\"isBucketed\":false,\"scale\":\"ratio\",\"sourceField\":\"duration_ms\"},\"col3\":{\"label\":\"P95 (ms)\",\"dataType\":\"number\",\"operationType\":\"percentile\",\"isBucketed\":false,\"scale\":\"ratio\",\"sourceField\":\"duration_ms\",\"params\":{\"percentile\":95}}},\"columnOrder\":[\"col1\",\"col2\",\"col3\"],\"incompleteColumns\":{}}}}},\"visualization\":{\"legend\":{\"isVisible\":true,\"position\":\"bottom\"},\"preferredSeriesType\":\"line\",\"layers\":[{\"layerId\":\"layer1\",\"accessors\":[\"col2\",\"col3\"],\"seriesType\":\"line\",\"layerType\":\"data\",\"xAccessor\":\"col1\"}],\"yTitle\":\"Durée (ms)\",\"xTitle\":\"Temps\"},\"query\":{\"query\":\"service_type: api AND duration_ms: *\",\"language\":\"kuery\"},\"filters\":[],\"datasourceMetaData\":{\"filterableIndexPatterns\":[{\"id\":\"all-logs-index-pattern\",\"title\":\"recommendation-*-logs-*\"}]},\"references\":[{\"type\":\"index-pattern\",\"id\":\"all-logs-index-pattern\",\"name\":\"indexpattern-datasource-layer-layer1\"}]}",
            "description": "Évolution du temps de réponse moyen et P95"
        },
        "references": [{"type":"index-pattern","id":"all-logs-index-pattern","name":"indexpattern-datasource-layer-layer1"}]
    }' "Temps de Réponse dans le Temps"

    # --- 7. Distribution des Codes HTTP ---
    create_saved_object "lens" "api-logs-status-code-distribution" '{
        "attributes": {
            "title": "Distribution des Codes HTTP",
            "visualizationType": "lnsPie",
            "state": "{\"datasourceStates\":{\"formBased\":{\"layers\":{\"layer1\":{\"columns\":{\"col1\":{\"label\":\"Code HTTP\",\"dataType\":\"number\",\"operationType\":\"terms\",\"isBucketed\":true,\"scale\":\"ordinal\",\"sourceField\":\"http_status\",\"params\":{\"size\":10,\"orderBy\":{\"type\":\"column\",\"columnId\":\"col2\"},\"orderDirection\":\"desc\"}},\"col2\":{\"label\":\"Nombre\",\"dataType\":\"number\",\"operationType\":\"count\",\"isBucketed\":false,\"scale\":\"ratio\",\"sourceField\":\"___records___\"}},\"columnOrder\":[\"col1\",\"col2\"],\"incompleteColumns\":{}}}}},\"visualization\":{\"shape\":\"donut\",\"layers\":[{\"layerId\":\"layer1\",\"primaryGroups\":[\"col1\"],\"metrics\":[\"col2\"],\"numberDisplay\":\"percent\",\"categoryDisplay\":\"default\",\"legendDisplay\":\"default\",\"layerType\":\"data\"}]},\"query\":{\"query\":\"http_status: *\",\"language\":\"kuery\"},\"filters\":[],\"datasourceMetaData\":{\"filterableIndexPatterns\":[{\"id\":\"all-logs-index-pattern\",\"title\":\"recommendation-*-logs-*\"}]},\"references\":[{\"type\":\"index-pattern\",\"id\":\"all-logs-index-pattern\",\"name\":\"indexpattern-datasource-layer-layer1\"}]}",
            "description": "Répartition des codes de statut HTTP"
        },
        "references": [{"type":"index-pattern","id":"all-logs-index-pattern","name":"indexpattern-datasource-layer-layer1"}]
    }' "Distribution des Codes HTTP"

    # --- 8. Catégorie de Temps de Réponse ---
    create_saved_object "lens" "api-logs-response-category" '{
        "attributes": {
            "title": "Catégorie de Temps de Réponse",
            "visualizationType": "lnsPie",
            "state": "{\"datasourceStates\":{\"formBased\":{\"layers\":{\"layer1\":{\"columns\":{\"col1\":{\"label\":\"Catégorie\",\"dataType\":\"string\",\"operationType\":\"terms\",\"isBucketed\":true,\"scale\":\"ordinal\",\"sourceField\":\"response_category\",\"params\":{\"size\":5,\"orderBy\":{\"type\":\"column\",\"columnId\":\"col2\"},\"orderDirection\":\"desc\"}},\"col2\":{\"label\":\"Nombre\",\"dataType\":\"number\",\"operationType\":\"count\",\"isBucketed\":false,\"scale\":\"ratio\",\"sourceField\":\"___records___\"}},\"columnOrder\":[\"col1\",\"col2\"],\"incompleteColumns\":{}}}}},\"visualization\":{\"shape\":\"pie\",\"layers\":[{\"layerId\":\"layer1\",\"primaryGroups\":[\"col1\"],\"metrics\":[\"col2\"],\"numberDisplay\":\"percent\",\"categoryDisplay\":\"default\",\"legendDisplay\":\"default\",\"layerType\":\"data\"}]},\"query\":{\"query\":\"response_category: *\",\"language\":\"kuery\"},\"filters\":[],\"datasourceMetaData\":{\"filterableIndexPatterns\":[{\"id\":\"all-logs-index-pattern\",\"title\":\"recommendation-*-logs-*\"}]},\"references\":[{\"type\":\"index-pattern\",\"id\":\"all-logs-index-pattern\",\"name\":\"indexpattern-datasource-layer-layer1\"}]}",
            "description": "Distribution fast/normal/slow/very_slow"
        },
        "references": [{"type":"index-pattern","id":"all-logs-index-pattern","name":"indexpattern-datasource-layer-layer1"}]
    }' "Catégorie de Temps de Réponse"

    # --- 9. Top 10 Endpoints ---
    create_saved_object "lens" "api-logs-top-endpoints" '{
        "attributes": {
            "title": "Top 10 Endpoints par Requêtes",
            "visualizationType": "lnsDatatable",
            "state": "{\"datasourceStates\":{\"formBased\":{\"layers\":{\"layer1\":{\"columns\":{\"col1\":{\"label\":\"Endpoint\",\"dataType\":\"string\",\"operationType\":\"terms\",\"isBucketed\":true,\"scale\":\"ordinal\",\"sourceField\":\"request_path\",\"params\":{\"size\":10,\"orderBy\":{\"type\":\"column\",\"columnId\":\"col2\"},\"orderDirection\":\"desc\"}},\"col2\":{\"label\":\"Requêtes\",\"dataType\":\"number\",\"operationType\":\"count\",\"isBucketed\":false,\"scale\":\"ratio\",\"sourceField\":\"___records___\"},\"col3\":{\"label\":\"Temps Moyen (ms)\",\"dataType\":\"number\",\"operationType\":\"average\",\"isBucketed\":false,\"scale\":\"ratio\",\"sourceField\":\"duration_ms\"}},\"columnOrder\":[\"col1\",\"col2\",\"col3\"],\"incompleteColumns\":{}}}}},\"visualization\":{\"layerId\":\"layer1\",\"layerType\":\"data\",\"columns\":[{\"columnId\":\"col1\",\"width\":300},{\"columnId\":\"col2\",\"alignment\":\"center\"},{\"columnId\":\"col3\",\"alignment\":\"center\"}],\"paging\":{\"size\":10,\"enabled\":true}},\"query\":{\"query\":\"request_path: * AND service_type: api\",\"language\":\"kuery\"},\"filters\":[],\"datasourceMetaData\":{\"filterableIndexPatterns\":[{\"id\":\"all-logs-index-pattern\",\"title\":\"recommendation-*-logs-*\"}]},\"references\":[{\"type\":\"index-pattern\",\"id\":\"all-logs-index-pattern\",\"name\":\"indexpattern-datasource-layer-layer1\"}]}",
            "description": "Les endpoints les plus sollicités"
        },
        "references": [{"type":"index-pattern","id":"all-logs-index-pattern","name":"indexpattern-datasource-layer-layer1"}]
    }' "Top 10 Endpoints"

    # --- 10. Requêtes par Méthode HTTP ---
    create_saved_object "lens" "api-logs-by-method" '{
        "attributes": {
            "title": "Requêtes par Méthode HTTP",
            "visualizationType": "lnsXY",
            "state": "{\"datasourceStates\":{\"formBased\":{\"layers\":{\"layer1\":{\"columns\":{\"col1\":{\"label\":\"Timestamp\",\"dataType\":\"date\",\"operationType\":\"date_histogram\",\"isBucketed\":true,\"scale\":\"interval\",\"sourceField\":\"@timestamp\",\"params\":{\"interval\":\"auto\"}},\"col2\":{\"label\":\"Méthode HTTP\",\"dataType\":\"string\",\"operationType\":\"terms\",\"isBucketed\":true,\"scale\":\"ordinal\",\"sourceField\":\"http_method\",\"params\":{\"size\":6,\"orderBy\":{\"type\":\"column\",\"columnId\":\"col3\"},\"orderDirection\":\"desc\"}},\"col3\":{\"label\":\"Nombre\",\"dataType\":\"number\",\"operationType\":\"count\",\"isBucketed\":false,\"scale\":\"ratio\",\"sourceField\":\"___records___\"}},\"columnOrder\":[\"col1\",\"col2\",\"col3\"],\"incompleteColumns\":{}}}}},\"visualization\":{\"legend\":{\"isVisible\":true,\"position\":\"right\"},\"preferredSeriesType\":\"bar_stacked\",\"layers\":[{\"layerId\":\"layer1\",\"accessors\":[\"col3\"],\"seriesType\":\"bar_stacked\",\"layerType\":\"data\",\"xAccessor\":\"col1\",\"splitAccessor\":\"col2\"}],\"yTitle\":\"Requêtes\",\"xTitle\":\"Temps\"},\"query\":{\"query\":\"http_method: *\",\"language\":\"kuery\"},\"filters\":[],\"datasourceMetaData\":{\"filterableIndexPatterns\":[{\"id\":\"all-logs-index-pattern\",\"title\":\"recommendation-*-logs-*\"}]},\"references\":[{\"type\":\"index-pattern\",\"id\":\"all-logs-index-pattern\",\"name\":\"indexpattern-datasource-layer-layer1\"}]}",
            "description": "Distribution GET, POST, PUT, DELETE"
        },
        "references": [{"type":"index-pattern","id":"all-logs-index-pattern","name":"indexpattern-datasource-layer-layer1"}]
    }' "Requêtes par Méthode HTTP"

    # --- 11. Logs par Service ---
    create_saved_object "lens" "api-logs-by-service" '{
        "attributes": {
            "title": "Logs par Service",
            "visualizationType": "lnsXY",
            "state": "{\"datasourceStates\":{\"formBased\":{\"layers\":{\"layer1\":{\"columns\":{\"col1\":{\"label\":\"Timestamp\",\"dataType\":\"date\",\"operationType\":\"date_histogram\",\"isBucketed\":true,\"scale\":\"interval\",\"sourceField\":\"@timestamp\",\"params\":{\"interval\":\"auto\"}},\"col2\":{\"label\":\"Service\",\"dataType\":\"string\",\"operationType\":\"terms\",\"isBucketed\":true,\"scale\":\"ordinal\",\"sourceField\":\"service_type\",\"params\":{\"size\":5,\"orderBy\":{\"type\":\"column\",\"columnId\":\"col3\"},\"orderDirection\":\"desc\"}},\"col3\":{\"label\":\"Nombre\",\"dataType\":\"number\",\"operationType\":\"count\",\"isBucketed\":false,\"scale\":\"ratio\",\"sourceField\":\"___records___\"}},\"columnOrder\":[\"col1\",\"col2\",\"col3\"],\"incompleteColumns\":{}}}}},\"visualization\":{\"legend\":{\"isVisible\":true,\"position\":\"right\"},\"preferredSeriesType\":\"area_stacked\",\"layers\":[{\"layerId\":\"layer1\",\"accessors\":[\"col3\"],\"seriesType\":\"area_stacked\",\"layerType\":\"data\",\"xAccessor\":\"col1\",\"splitAccessor\":\"col2\"}],\"yTitle\":\"Logs\",\"xTitle\":\"Temps\"},\"query\":{\"query\":\"\",\"language\":\"kuery\"},\"filters\":[],\"datasourceMetaData\":{\"filterableIndexPatterns\":[{\"id\":\"all-logs-index-pattern\",\"title\":\"recommendation-*-logs-*\"}]},\"references\":[{\"type\":\"index-pattern\",\"id\":\"all-logs-index-pattern\",\"name\":\"indexpattern-datasource-layer-layer1\"}]}",
            "description": "Volume de logs par type de service"
        },
        "references": [{"type":"index-pattern","id":"all-logs-index-pattern","name":"indexpattern-datasource-layer-layer1"}]
    }' "Logs par Service"

    # --- 12. Logs par Niveau ---
    create_saved_object "lens" "api-logs-by-level" '{
        "attributes": {
            "title": "Logs par Niveau",
            "visualizationType": "lnsXY",
            "state": "{\"datasourceStates\":{\"formBased\":{\"layers\":{\"layer1\":{\"columns\":{\"col1\":{\"label\":\"Timestamp\",\"dataType\":\"date\",\"operationType\":\"date_histogram\",\"isBucketed\":true,\"scale\":\"interval\",\"sourceField\":\"@timestamp\",\"params\":{\"interval\":\"auto\"}},\"col2\":{\"label\":\"Niveau\",\"dataType\":\"string\",\"operationType\":\"terms\",\"isBucketed\":true,\"scale\":\"ordinal\",\"sourceField\":\"level\",\"params\":{\"size\":5,\"orderBy\":{\"type\":\"column\",\"columnId\":\"col3\"},\"orderDirection\":\"desc\"}},\"col3\":{\"label\":\"Nombre\",\"dataType\":\"number\",\"operationType\":\"count\",\"isBucketed\":false,\"scale\":\"ratio\",\"sourceField\":\"___records___\"}},\"columnOrder\":[\"col1\",\"col2\",\"col3\"],\"incompleteColumns\":{}}}}},\"visualization\":{\"legend\":{\"isVisible\":true,\"position\":\"right\"},\"preferredSeriesType\":\"bar_stacked\",\"layers\":[{\"layerId\":\"layer1\",\"accessors\":[\"col3\"],\"seriesType\":\"bar_stacked\",\"layerType\":\"data\",\"xAccessor\":\"col1\",\"splitAccessor\":\"col2\"}],\"yTitle\":\"Logs\",\"xTitle\":\"Temps\"},\"query\":{\"query\":\"\",\"language\":\"kuery\"},\"filters\":[],\"datasourceMetaData\":{\"filterableIndexPatterns\":[{\"id\":\"all-logs-index-pattern\",\"title\":\"recommendation-*-logs-*\"}]},\"references\":[{\"type\":\"index-pattern\",\"id\":\"all-logs-index-pattern\",\"name\":\"indexpattern-datasource-layer-layer1\"}]}",
            "description": "Distribution INFO, WARNING, ERROR, CRITICAL"
        },
        "references": [{"type":"index-pattern","id":"all-logs-index-pattern","name":"indexpattern-datasource-layer-layer1"}]
    }' "Logs par Niveau"

    # --- 13. Erreurs Récentes ---
    create_saved_object "lens" "api-logs-recent-errors" '{
        "attributes": {
            "title": "Erreurs Récentes",
            "visualizationType": "lnsDatatable",
            "state": "{\"datasourceStates\":{\"formBased\":{\"layers\":{\"layer1\":{\"columns\":{\"col1\":{\"label\":\"Timestamp\",\"dataType\":\"date\",\"operationType\":\"date_histogram\",\"isBucketed\":true,\"scale\":\"interval\",\"sourceField\":\"@timestamp\",\"params\":{\"interval\":\"1h\"}},\"col2\":{\"label\":\"Endpoint\",\"dataType\":\"string\",\"operationType\":\"terms\",\"isBucketed\":true,\"scale\":\"ordinal\",\"sourceField\":\"request_path\",\"params\":{\"size\":20,\"orderBy\":{\"type\":\"column\",\"columnId\":\"col4\"},\"orderDirection\":\"desc\"}},\"col3\":{\"label\":\"Status\",\"dataType\":\"number\",\"operationType\":\"terms\",\"isBucketed\":true,\"scale\":\"ordinal\",\"sourceField\":\"http_status\",\"params\":{\"size\":10,\"orderBy\":{\"type\":\"column\",\"columnId\":\"col4\"},\"orderDirection\":\"desc\"}},\"col4\":{\"label\":\"Count\",\"dataType\":\"number\",\"operationType\":\"count\",\"isBucketed\":false,\"scale\":\"ratio\",\"sourceField\":\"___records___\"}},\"columnOrder\":[\"col1\",\"col2\",\"col3\",\"col4\"],\"incompleteColumns\":{}}}}},\"visualization\":{\"layerId\":\"layer1\",\"layerType\":\"data\",\"columns\":[{\"columnId\":\"col1\"},{\"columnId\":\"col2\",\"width\":250},{\"columnId\":\"col3\",\"alignment\":\"center\"},{\"columnId\":\"col4\",\"alignment\":\"center\"}],\"paging\":{\"size\":10,\"enabled\":true}},\"query\":{\"query\":\"http_status >= 400\",\"language\":\"kuery\"},\"filters\":[],\"datasourceMetaData\":{\"filterableIndexPatterns\":[{\"id\":\"all-logs-index-pattern\",\"title\":\"recommendation-*-logs-*\"}]},\"references\":[{\"type\":\"index-pattern\",\"id\":\"all-logs-index-pattern\",\"name\":\"indexpattern-datasource-layer-layer1\"}]}",
            "description": "Tableau des erreurs avec détails"
        },
        "references": [{"type":"index-pattern","id":"all-logs-index-pattern","name":"indexpattern-datasource-layer-layer1"}]
    }' "Erreurs Récentes"

    # --- 14. Requêtes Lentes ---
    create_saved_object "lens" "api-logs-slow-requests" '{
        "attributes": {
            "title": "Requêtes Lentes (>500ms)",
            "visualizationType": "lnsDatatable",
            "state": "{\"datasourceStates\":{\"formBased\":{\"layers\":{\"layer1\":{\"columns\":{\"col1\":{\"label\":\"Endpoint\",\"dataType\":\"string\",\"operationType\":\"terms\",\"isBucketed\":true,\"scale\":\"ordinal\",\"sourceField\":\"request_path\",\"params\":{\"size\":15,\"orderBy\":{\"type\":\"column\",\"columnId\":\"col3\"},\"orderDirection\":\"desc\"}},\"col2\":{\"label\":\"Méthode\",\"dataType\":\"string\",\"operationType\":\"terms\",\"isBucketed\":true,\"scale\":\"ordinal\",\"sourceField\":\"http_method\",\"params\":{\"size\":6,\"orderBy\":{\"type\":\"column\",\"columnId\":\"col3\"},\"orderDirection\":\"desc\"}},\"col3\":{\"label\":\"Temps Moyen (ms)\",\"dataType\":\"number\",\"operationType\":\"average\",\"isBucketed\":false,\"scale\":\"ratio\",\"sourceField\":\"duration_ms\"},\"col4\":{\"label\":\"Max (ms)\",\"dataType\":\"number\",\"operationType\":\"max\",\"isBucketed\":false,\"scale\":\"ratio\",\"sourceField\":\"duration_ms\"},\"col5\":{\"label\":\"Nombre\",\"dataType\":\"number\",\"operationType\":\"count\",\"isBucketed\":false,\"scale\":\"ratio\",\"sourceField\":\"___records___\"}},\"columnOrder\":[\"col1\",\"col2\",\"col3\",\"col4\",\"col5\"],\"incompleteColumns\":{}}}}},\"visualization\":{\"layerId\":\"layer1\",\"layerType\":\"data\",\"columns\":[{\"columnId\":\"col1\",\"width\":250},{\"columnId\":\"col2\",\"alignment\":\"center\"},{\"columnId\":\"col3\",\"alignment\":\"center\"},{\"columnId\":\"col4\",\"alignment\":\"center\"},{\"columnId\":\"col5\",\"alignment\":\"center\"}],\"paging\":{\"size\":10,\"enabled\":true}},\"query\":{\"query\":\"duration_ms > 500\",\"language\":\"kuery\"},\"filters\":[],\"datasourceMetaData\":{\"filterableIndexPatterns\":[{\"id\":\"all-logs-index-pattern\",\"title\":\"recommendation-*-logs-*\"}]},\"references\":[{\"type\":\"index-pattern\",\"id\":\"all-logs-index-pattern\",\"name\":\"indexpattern-datasource-layer-layer1\"}]}",
            "description": "Requêtes avec temps de réponse élevé"
        },
        "references": [{"type":"index-pattern","id":"all-logs-index-pattern","name":"indexpattern-datasource-layer-layer1"}]
    }' "Requêtes Lentes (>500ms)"

    # --- 15. Correlation ID Tracking ---
    create_saved_object "lens" "api-logs-correlation-tracking" '{
        "attributes": {
            "title": "Requêtes par Correlation ID",
            "visualizationType": "lnsDatatable",
            "state": "{\"datasourceStates\":{\"formBased\":{\"layers\":{\"layer1\":{\"columns\":{\"col1\":{\"label\":\"Correlation ID\",\"dataType\":\"string\",\"operationType\":\"terms\",\"isBucketed\":true,\"scale\":\"ordinal\",\"sourceField\":\"request_id\",\"params\":{\"size\":20,\"orderBy\":{\"type\":\"column\",\"columnId\":\"col3\"},\"orderDirection\":\"desc\"}},\"col2\":{\"label\":\"Service\",\"dataType\":\"string\",\"operationType\":\"terms\",\"isBucketed\":true,\"scale\":\"ordinal\",\"sourceField\":\"service_type\",\"params\":{\"size\":5,\"orderBy\":{\"type\":\"column\",\"columnId\":\"col3\"},\"orderDirection\":\"desc\"}},\"col3\":{\"label\":\"Logs\",\"dataType\":\"number\",\"operationType\":\"count\",\"isBucketed\":false,\"scale\":\"ratio\",\"sourceField\":\"___records___\"},\"col4\":{\"label\":\"Durée Moyenne (ms)\",\"dataType\":\"number\",\"operationType\":\"average\",\"isBucketed\":false,\"scale\":\"ratio\",\"sourceField\":\"duration_ms\"}},\"columnOrder\":[\"col1\",\"col2\",\"col3\",\"col4\"],\"incompleteColumns\":{}}}}},\"visualization\":{\"layerId\":\"layer1\",\"layerType\":\"data\",\"columns\":[{\"columnId\":\"col1\",\"width\":300},{\"columnId\":\"col2\",\"alignment\":\"center\"},{\"columnId\":\"col3\",\"alignment\":\"center\"},{\"columnId\":\"col4\",\"alignment\":\"center\"}],\"paging\":{\"size\":10,\"enabled\":true}},\"query\":{\"query\":\"request_id: *\",\"language\":\"kuery\"},\"filters\":[],\"datasourceMetaData\":{\"filterableIndexPatterns\":[{\"id\":\"all-logs-index-pattern\",\"title\":\"recommendation-*-logs-*\"}]},\"references\":[{\"type\":\"index-pattern\",\"id\":\"all-logs-index-pattern\",\"name\":\"indexpattern-datasource-layer-layer1\"}]}",
            "description": "Suivi bout-en-bout des requêtes"
        },
        "references": [{"type":"index-pattern","id":"all-logs-index-pattern","name":"indexpattern-datasource-layer-layer1"}]
    }' "Requêtes par Correlation ID"
}

# =============================================================================
# Create the Dashboard
# =============================================================================
create_dashboard() {
    log_info "Création du dashboard..."

    create_saved_object "dashboard" "api-logs-dashboard" '{
        "attributes": {
            "title": "API Logs Dashboard - AR_AS",
            "description": "Dashboard complet pour la visualisation des logs API du système de recommandation AR_AS",
            "panelsJSON": "[{\"version\":\"8.11.0\",\"type\":\"lens\",\"gridData\":{\"x\":0,\"y\":0,\"w\":12,\"h\":8,\"i\":\"panel_1\"},\"panelIndex\":\"panel_1\",\"embeddableConfig\":{\"enhancements\":{}},\"title\":\"Total Requêtes API\",\"panelRefName\":\"panel_panel_1\"},{\"version\":\"8.11.0\",\"type\":\"lens\",\"gridData\":{\"x\":12,\"y\":0,\"w\":12,\"h\":8,\"i\":\"panel_2\"},\"panelIndex\":\"panel_2\",\"embeddableConfig\":{\"enhancements\":{}},\"title\":\"Taux d Erreurs\",\"panelRefName\":\"panel_panel_2\"},{\"version\":\"8.11.0\",\"type\":\"lens\",\"gridData\":{\"x\":24,\"y\":0,\"w\":12,\"h\":8,\"i\":\"panel_3\"},\"panelIndex\":\"panel_3\",\"embeddableConfig\":{\"enhancements\":{}},\"title\":\"Temps de Réponse Moyen\",\"panelRefName\":\"panel_panel_3\"},{\"version\":\"8.11.0\",\"type\":\"lens\",\"gridData\":{\"x\":36,\"y\":0,\"w\":12,\"h\":8,\"i\":\"panel_4\"},\"panelIndex\":\"panel_4\",\"embeddableConfig\":{\"enhancements\":{}},\"title\":\"Temps de Réponse P95\",\"panelRefName\":\"panel_panel_4\"},{\"version\":\"8.11.0\",\"type\":\"lens\",\"gridData\":{\"x\":0,\"y\":8,\"w\":32,\"h\":14,\"i\":\"panel_5\"},\"panelIndex\":\"panel_5\",\"embeddableConfig\":{\"enhancements\":{}},\"title\":\"Requêtes API dans le Temps\",\"panelRefName\":\"panel_panel_5\"},{\"version\":\"8.11.0\",\"type\":\"lens\",\"gridData\":{\"x\":32,\"y\":8,\"w\":16,\"h\":14,\"i\":\"panel_6\"},\"panelIndex\":\"panel_6\",\"embeddableConfig\":{\"enhancements\":{}},\"title\":\"Distribution des Codes HTTP\",\"panelRefName\":\"panel_panel_6\"},{\"version\":\"8.11.0\",\"type\":\"lens\",\"gridData\":{\"x\":0,\"y\":22,\"w\":32,\"h\":14,\"i\":\"panel_7\"},\"panelIndex\":\"panel_7\",\"embeddableConfig\":{\"enhancements\":{}},\"title\":\"Temps de Réponse dans le Temps\",\"panelRefName\":\"panel_panel_7\"},{\"version\":\"8.11.0\",\"type\":\"lens\",\"gridData\":{\"x\":32,\"y\":22,\"w\":16,\"h\":14,\"i\":\"panel_8\"},\"panelIndex\":\"panel_8\",\"embeddableConfig\":{\"enhancements\":{}},\"title\":\"Catégorie de Temps de Réponse\",\"panelRefName\":\"panel_panel_8\"},{\"version\":\"8.11.0\",\"type\":\"lens\",\"gridData\":{\"x\":0,\"y\":36,\"w\":48,\"h\":14,\"i\":\"panel_9\"},\"panelIndex\":\"panel_9\",\"embeddableConfig\":{\"enhancements\":{}},\"title\":\"Top 10 Endpoints\",\"panelRefName\":\"panel_panel_9\"},{\"version\":\"8.11.0\",\"type\":\"lens\",\"gridData\":{\"x\":0,\"y\":50,\"w\":24,\"h\":14,\"i\":\"panel_10\"},\"panelIndex\":\"panel_10\",\"embeddableConfig\":{\"enhancements\":{}},\"title\":\"Requêtes par Méthode HTTP\",\"panelRefName\":\"panel_panel_10\"},{\"version\":\"8.11.0\",\"type\":\"lens\",\"gridData\":{\"x\":24,\"y\":50,\"w\":24,\"h\":14,\"i\":\"panel_11\"},\"panelIndex\":\"panel_11\",\"embeddableConfig\":{\"enhancements\":{}},\"title\":\"Logs par Service\",\"panelRefName\":\"panel_panel_11\"},{\"version\":\"8.11.0\",\"type\":\"lens\",\"gridData\":{\"x\":0,\"y\":64,\"w\":48,\"h\":12,\"i\":\"panel_12\"},\"panelIndex\":\"panel_12\",\"embeddableConfig\":{\"enhancements\":{}},\"title\":\"Logs par Niveau\",\"panelRefName\":\"panel_panel_12\"},{\"version\":\"8.11.0\",\"type\":\"lens\",\"gridData\":{\"x\":0,\"y\":76,\"w\":24,\"h\":14,\"i\":\"panel_13\"},\"panelIndex\":\"panel_13\",\"embeddableConfig\":{\"enhancements\":{}},\"title\":\"Erreurs Récentes\",\"panelRefName\":\"panel_panel_13\"},{\"version\":\"8.11.0\",\"type\":\"lens\",\"gridData\":{\"x\":24,\"y\":76,\"w\":24,\"h\":14,\"i\":\"panel_14\"},\"panelIndex\":\"panel_14\",\"embeddableConfig\":{\"enhancements\":{}},\"title\":\"Requêtes Lentes (>500ms)\",\"panelRefName\":\"panel_panel_14\"},{\"version\":\"8.11.0\",\"type\":\"lens\",\"gridData\":{\"x\":0,\"y\":90,\"w\":48,\"h\":14,\"i\":\"panel_15\"},\"panelIndex\":\"panel_15\",\"embeddableConfig\":{\"enhancements\":{}},\"title\":\"Requêtes par Correlation ID\",\"panelRefName\":\"panel_panel_15\"}]",
            "optionsJSON": "{\"useMargins\":true,\"syncColors\":true,\"syncCursor\":true,\"syncTooltips\":false,\"hidePanelTitles\":false}",
            "timeRestore": true,
            "timeTo": "now",
            "timeFrom": "now-24h",
            "refreshInterval": { "pause": false, "value": 30000 },
            "kibanaSavedObjectMeta": {
                "searchSourceJSON": "{\"query\":{\"query\":\"\",\"language\":\"kuery\"},\"filter\":[]}"
            }
        },
        "references": [
            {"name":"panel_panel_1","type":"lens","id":"api-logs-total-requests"},
            {"name":"panel_panel_2","type":"lens","id":"api-logs-error-rate"},
            {"name":"panel_panel_3","type":"lens","id":"api-logs-avg-response-time"},
            {"name":"panel_panel_4","type":"lens","id":"api-logs-p95-response-time"},
            {"name":"panel_panel_5","type":"lens","id":"api-logs-requests-over-time"},
            {"name":"panel_panel_6","type":"lens","id":"api-logs-status-code-distribution"},
            {"name":"panel_panel_7","type":"lens","id":"api-logs-response-time-over-time"},
            {"name":"panel_panel_8","type":"lens","id":"api-logs-response-category"},
            {"name":"panel_panel_9","type":"lens","id":"api-logs-top-endpoints"},
            {"name":"panel_panel_10","type":"lens","id":"api-logs-by-method"},
            {"name":"panel_panel_11","type":"lens","id":"api-logs-by-service"},
            {"name":"panel_panel_12","type":"lens","id":"api-logs-by-level"},
            {"name":"panel_panel_13","type":"lens","id":"api-logs-recent-errors"},
            {"name":"panel_panel_14","type":"lens","id":"api-logs-slow-requests"},
            {"name":"panel_panel_15","type":"lens","id":"api-logs-correlation-tracking"}
        ]
    }' "API Logs Dashboard - AR_AS"
}

# =============================================================================
# Main
# =============================================================================
main() {
    echo "=============================================="
    echo "  AR_AS - Setup Kibana API Logs Dashboard"
    echo "=============================================="
    echo ""

    wait_for_elasticsearch
    wait_for_kibana
    echo ""
    create_index_template
    echo ""
    create_data_views
    echo ""
    create_visualizations
    echo ""
    create_dashboard

    echo ""
    echo "=============================================="
    log_success "Setup terminé! 15 visualisations + 1 dashboard créés"
    echo ""
    echo "  Dashboard : ${KIBANA_URL}/app/dashboards#/view/api-logs-dashboard"
    echo "  Credentials : ${ELASTIC_USER} / (voir .env)"
    echo "=============================================="
}

main "$@"
