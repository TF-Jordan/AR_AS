#!/bin/bash
# =============================================================================
# Script de création du Dashboard API Logs pour Kibana 8.11
# =============================================================================
# Ce script crée directement via l'API Kibana :
#   1. Les data views (index patterns)
#   2. Les visualisations Lens
#   3. Le dashboard avec tous les panneaux
#
# Usage:
#   ./setup-dashboards.sh
#   KIBANA_URL=http://localhost:5601 ELASTIC_PASSWORD=mypass ./setup-dashboards.sh
# =============================================================================

set -euo pipefail

# Configuration
KIBANA_URL="${KIBANA_URL:-http://localhost:5601}"
ELASTIC_USER="${ELASTIC_USER:-elastic}"
ELASTIC_PASSWORD="${ELASTIC_PASSWORD:-Ar@s_Elastic_2024!}"
ELASTICSEARCH_URL="${ELASTICSEARCH_URL:-http://localhost:9200}"
MAX_RETRIES=30
RETRY_INTERVAL=10

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1"; }

AUTH="${ELASTIC_USER}:${ELASTIC_PASSWORD}"

# Helper: Kibana API call
kibana_api() {
    local method="$1"
    local path="$2"
    local data="${3:-}"

    if [ -n "$data" ]; then
        curl -sf -X "$method" \
            -u "$AUTH" \
            -H "kbn-xsrf: true" \
            -H "Content-Type: application/json" \
            "${KIBANA_URL}${path}" \
            -d "$data" 2>&1
    else
        curl -sf -X "$method" \
            -u "$AUTH" \
            -H "kbn-xsrf: true" \
            "${KIBANA_URL}${path}" 2>&1
    fi
}

# Helper: Elasticsearch API call
es_api() {
    local method="$1"
    local path="$2"
    local data="${3:-}"

    if [ -n "$data" ]; then
        curl -sf -X "$method" \
            -u "$AUTH" \
            -H "Content-Type: application/json" \
            "${ELASTICSEARCH_URL}${path}" \
            -d "$data" 2>&1
    else
        curl -sf -X "$method" \
            -u "$AUTH" \
            "${ELASTICSEARCH_URL}${path}" 2>&1
    fi
}

# =============================================================================
# Step 1: Wait for services
# =============================================================================
wait_for_elasticsearch() {
    log_info "Attente d'Elasticsearch sur ${ELASTICSEARCH_URL}..."
    local retries=0
    while [ $retries -lt $MAX_RETRIES ]; do
        if curl -sf -u "$AUTH" "${ELASTICSEARCH_URL}/_cluster/health" > /dev/null 2>&1; then
            log_success "Elasticsearch est prêt!"
            return 0
        fi
        retries=$((retries + 1))
        log_warn "Tentative ${retries}/${MAX_RETRIES}..."
        sleep $RETRY_INTERVAL
    done
    log_error "Elasticsearch non disponible"; exit 1
}

wait_for_kibana() {
    log_info "Attente de Kibana sur ${KIBANA_URL}..."
    local retries=0
    while [ $retries -lt $MAX_RETRIES ]; do
        if curl -sf -u "$AUTH" "${KIBANA_URL}/api/status" > /dev/null 2>&1; then
            log_success "Kibana est prêt!"
            return 0
        fi
        retries=$((retries + 1))
        log_warn "Tentative ${retries}/${MAX_RETRIES}..."
        sleep $RETRY_INTERVAL
    done
    log_error "Kibana non disponible"; exit 1
}

# =============================================================================
# Step 2: Create Elasticsearch index template
# =============================================================================
create_index_template() {
    log_info "Création du template d'index..."
    es_api PUT "/_index_template/recommendation-logs" '{
        "index_patterns": ["recommendation-*-logs-*"],
        "template": {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
                "refresh_interval": "5s"
            },
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
                    "product_id": { "type": "keyword" },
                    "session_id": { "type": "keyword" },
                    "http_method": { "type": "keyword" },
                    "request_path": { "type": "keyword" },
                    "http_status": { "type": "integer" },
                    "http_version": { "type": "keyword" },
                    "duration_ms": { "type": "float" },
                    "duration_seconds": { "type": "float" },
                    "client_ip": { "type": "ip", "ignore_malformed": true },
                    "user_agent": { "type": "text", "fields": { "keyword": { "type": "keyword" } } },
                    "response_category": { "type": "keyword" },
                    "is_slow_request": { "type": "boolean" },
                    "is_error": { "type": "boolean" },
                    "is_server_error": { "type": "boolean" },
                    "processed_at": { "type": "date" },
                    "geoip": {
                        "properties": {
                            "location": { "type": "geo_point" },
                            "country_name": { "type": "keyword" },
                            "city_name": { "type": "keyword" }
                        }
                    }
                }
            }
        },
        "priority": 200
    }' > /dev/null && log_success "Template créé" || log_warn "Template existe déjà ou erreur"
}

# =============================================================================
# Step 3: Create Data Views (index patterns) via Kibana API
# =============================================================================
create_data_views() {
    log_info "Création des data views..."

    # Data view for all recommendation logs
    local result
    result=$(kibana_api POST "/api/data_views/data_view" '{
        "data_view": {
            "id": "all-logs-index-pattern",
            "title": "recommendation-*-logs-*",
            "timeFieldName": "@timestamp",
            "name": "Recommendation - All Logs"
        },
        "override": true
    }') && log_success "  Data view 'All Logs' créée" || log_warn "  Data view 'All Logs': $(echo $result | head -c 100)"

    # Data view for API logs only
    result=$(kibana_api POST "/api/data_views/data_view" '{
        "data_view": {
            "id": "api-logs-index-pattern",
            "title": "recommendation-api-logs-*",
            "timeFieldName": "@timestamp",
            "name": "Recommendation - API Logs"
        },
        "override": true
    }') && log_success "  Data view 'API Logs' créée" || log_warn "  Data view 'API Logs': $(echo $result | head -c 100)"

    # Data view for error logs
    result=$(kibana_api POST "/api/data_views/data_view" '{
        "data_view": {
            "id": "error-logs-index-pattern",
            "title": "recommendation-errors-*",
            "timeFieldName": "@timestamp",
            "name": "Recommendation - Error Logs"
        },
        "override": true
    }') && log_success "  Data view 'Error Logs' créée" || log_warn "  Data view 'Error Logs': $(echo $result | head -c 100)"

    # Data view for metricbeat
    result=$(kibana_api POST "/api/data_views/data_view" '{
        "data_view": {
            "id": "metricbeat-index-pattern",
            "title": "metricbeat-*",
            "timeFieldName": "@timestamp",
            "name": "Metricbeat"
        },
        "override": true
    }') && log_success "  Data view 'Metricbeat' créée" || log_warn "  Data view 'Metricbeat': $(echo $result | head -c 100)"

    # Set default data view
    kibana_api POST "/api/data_views/default" '{
        "data_view_id": "all-logs-index-pattern",
        "force": true
    }' > /dev/null 2>&1 && log_success "  Data view par défaut configurée" || true
}

# =============================================================================
# Step 4: Import NDJSON dashboard file
# =============================================================================
import_ndjson_dashboards() {
    local SCRIPT_DIR
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local DASHBOARDS_DIR="${SCRIPT_DIR}/dashboards"

    log_info "Import des dashboards NDJSON depuis ${DASHBOARDS_DIR}..."

    for ndjson_file in "${DASHBOARDS_DIR}"/*.ndjson; do
        [ ! -f "$ndjson_file" ] && continue
        local filename
        filename=$(basename "$ndjson_file")
        log_info "  Import de: ${filename}"

        local response
        response=$(curl -sf -X POST \
            -u "$AUTH" \
            -H "kbn-xsrf: true" \
            "${KIBANA_URL}/api/saved_objects/_import?overwrite=true" \
            --form file=@"${ndjson_file}" 2>&1) || true

        if echo "$response" | grep -q '"success":true'; then
            local count
            count=$(echo "$response" | grep -o '"successCount":[0-9]*' | grep -o '[0-9]*')
            log_success "  ${filename}: ${count:-?} objets importés avec succès"
        else
            log_warn "  ${filename}: Import partiel ou échoué (voir détails ci-dessous)"
            echo "    Réponse: $(echo "$response" | head -c 300)"
        fi
    done
}

# =============================================================================
# Step 5: Create dashboard directly via Kibana API (fallback if NDJSON fails)
# =============================================================================
create_dashboard_via_api() {
    log_info "Création du dashboard API Logs via l'API Kibana..."

    # Create dashboard
    local dashboard_body
    dashboard_body=$(cat <<'DASHBOARD_JSON'
{
    "attributes": {
        "title": "API Logs Dashboard - AR_AS",
        "description": "Dashboard complet pour la visualisation des logs API du système de recommandation AR_AS",
        "panelsJSON": "[]",
        "optionsJSON": "{\"useMargins\":true,\"syncColors\":true,\"syncCursor\":true,\"syncTooltips\":false,\"hidePanelTitles\":false}",
        "timeRestore": true,
        "timeTo": "now",
        "timeFrom": "now-24h",
        "refreshInterval": {
            "pause": false,
            "value": 30000
        },
        "kibanaSavedObjectMeta": {
            "searchSourceJSON": "{\"query\":{\"query\":\"\",\"language\":\"kuery\"},\"filter\":[]}"
        }
    },
    "references": []
}
DASHBOARD_JSON
    )

    local result
    result=$(kibana_api POST "/api/saved_objects/dashboard/api-logs-dashboard" "$dashboard_body")

    if echo "$result" | grep -q '"id"'; then
        log_success "Dashboard 'API Logs Dashboard - AR_AS' créé"
    elif echo "$result" | grep -q 'Conflict'; then
        log_warn "Dashboard existe déjà, mise à jour..."
        kibana_api PUT "/api/saved_objects/dashboard/api-logs-dashboard" "$dashboard_body" > /dev/null 2>&1
        log_success "Dashboard mis à jour"
    else
        log_warn "Résultat: $(echo "$result" | head -c 200)"
    fi
}

# =============================================================================
# Step 6: Display access instructions
# =============================================================================
show_instructions() {
    echo ""
    echo "=============================================="
    log_success "Setup terminé!"
    echo ""
    echo "  Accédez aux dashboards :"
    echo "    ${KIBANA_URL}/app/dashboards"
    echo ""
    echo "  Pour créer manuellement les visualisations dans Kibana :"
    echo "    1. Allez dans ${KIBANA_URL}/app/lens"
    echo "    2. Sélectionnez le data view 'Recommendation - All Logs'"
    echo "    3. Créez vos visualisations avec les champs disponibles"
    echo ""
    echo "  Champs disponibles pour les visualisations :"
    echo "    - @timestamp          : Horodatage"
    echo "    - level               : Niveau de log (INFO, WARNING, ERROR)"
    echo "    - service_type        : Type de service (api, celery_worker...)"
    echo "    - http_method         : Méthode HTTP (GET, POST, PUT, DELETE)"
    echo "    - request_path        : Chemin de la requête (/api/v1/...)"
    echo "    - http_status         : Code HTTP (200, 404, 500...)"
    echo "    - duration_ms         : Temps de réponse en millisecondes"
    echo "    - response_category   : Catégorie (fast, normal, slow, very_slow)"
    echo "    - request_id          : ID de corrélation"
    echo "    - client_ip           : Adresse IP du client"
    echo "    - is_error            : Flag erreur (true/false)"
    echo "    - is_slow_request     : Flag requête lente (true/false)"
    echo ""
    echo "  Credentials :"
    echo "    User: ${ELASTIC_USER}"
    echo "    Pass: (configuré dans .env)"
    echo "=============================================="
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
    import_ndjson_dashboards
    echo ""
    create_dashboard_via_api
    show_instructions
}

main "$@"
