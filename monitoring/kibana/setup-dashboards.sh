#!/bin/bash
# =============================================================================
# Script de création du Dashboard API Logs pour Kibana 8.11
# =============================================================================
# Utilise l'API officielle /api/saved_objects/_import avec un fichier NDJSON
# généré par generate-dashboard-ndjson.py
#
# Usage:
#   ./setup-dashboards.sh
#   KIBANA_URL=http://localhost:5601 ELASTIC_PASSWORD=mypass ./setup-dashboards.sh
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

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
wait_for_elasticsearch() {
    log_info "Attente d'Elasticsearch..."
    local r=0
    while [ $r -lt $MAX_RETRIES ]; do
        if curl -sf -u "$AUTH" "${ELASTICSEARCH_URL}/_cluster/health" > /dev/null 2>&1; then
            log_success "Elasticsearch prêt!"
            return 0
        fi
        r=$((r + 1)); sleep $RETRY_INTERVAL
    done
    log_error "Elasticsearch non disponible"; exit 1
}

wait_for_kibana() {
    log_info "Attente de Kibana..."
    local r=0
    while [ $r -lt $MAX_RETRIES ]; do
        if curl -sf -u "$AUTH" "${KIBANA_URL}/api/status" > /dev/null 2>&1; then
            log_success "Kibana prêt!"
            return 0
        fi
        r=$((r + 1)); sleep $RETRY_INTERVAL
    done
    log_error "Kibana non disponible"; exit 1
}

# =============================================================================
create_index_template() {
    log_info "Création du template d'index..."
    local response
    response=$(curl -s -w "\n%{http_code}" -X PUT -u "$AUTH" \
        -H "Content-Type: application/json" \
        "${ELASTICSEARCH_URL}/_index_template/recommendation-logs" \
        -d '{
            "index_patterns": ["recommendation-*-logs-*"],
            "template": {
                "settings": { "number_of_shards": 1, "number_of_replicas": 0 },
                "mappings": {
                    "properties": {
                        "@timestamp": { "type": "date" },
                        "level": { "type": "text", "fields": { "keyword": { "type": "keyword" } } },
                        "logger": { "type": "keyword" },
                        "log_message": { "type": "text", "fields": { "keyword": { "type": "keyword" } } },
                        "service": { "type": "keyword" },
                        "service_type": { "type": "text", "fields": { "keyword": { "type": "keyword" } } },
                        "container_name": { "type": "keyword" },
                        "request_id": { "type": "text", "fields": { "keyword": { "type": "keyword" } } },
                        "correlation_id": { "type": "text", "fields": { "keyword": { "type": "keyword" } } },
                        "user_id": { "type": "keyword" },
                        "session_id": { "type": "keyword" },
                        "http_method": { "type": "text", "fields": { "keyword": { "type": "keyword" } } },
                        "request_path": { "type": "text", "fields": { "keyword": { "type": "keyword" } } },
                        "http_status": { "type": "integer" },
                        "duration_ms": { "type": "float" },
                        "duration_seconds": { "type": "float" },
                        "client_ip": { "type": "ip", "ignore_malformed": true },
                        "user_agent": { "type": "text", "fields": { "keyword": { "type": "keyword" } } },
                        "response_category": { "type": "text", "fields": { "keyword": { "type": "keyword" } } },
                        "is_slow_request": { "type": "boolean" },
                        "is_error": { "type": "boolean" },
                        "is_server_error": { "type": "boolean" },
                        "event_type": { "type": "keyword" }
                    }
                }
            },
            "priority": 200
        }' 2>&1)

    local http_code
    http_code=$(echo "$response" | tail -1)
    if [ "$http_code" = "200" ]; then
        log_success "Template créé"
    else
        log_warn "Template: HTTP ${http_code}"
    fi
}

# =============================================================================
update_existing_mappings() {
    log_info "Mise à jour des mappings des index existants..."
    local indices
    indices=$(curl -sf -u "$AUTH" "${ELASTICSEARCH_URL}/_cat/indices/recommendation-*-logs-*?h=index" 2>/dev/null || echo "")
    if [ -z "$indices" ]; then
        log_warn "Aucun index existant trouvé"
        return 0
    fi

    local mapping='{
        "properties": {
            "level": { "type": "text", "fields": { "keyword": { "type": "keyword" } } },
            "service_type": { "type": "text", "fields": { "keyword": { "type": "keyword" } } },
            "http_method": { "type": "text", "fields": { "keyword": { "type": "keyword" } } },
            "request_path": { "type": "text", "fields": { "keyword": { "type": "keyword" } } },
            "response_category": { "type": "text", "fields": { "keyword": { "type": "keyword" } } },
            "request_id": { "type": "text", "fields": { "keyword": { "type": "keyword" } } },
            "correlation_id": { "type": "text", "fields": { "keyword": { "type": "keyword" } } }
        }
    }'

    for idx in $indices; do
        curl -sf -X PUT -u "$AUTH" -H "Content-Type: application/json" \
            "${ELASTICSEARCH_URL}/${idx}/_mapping" \
            -d "$mapping" > /dev/null 2>&1 \
            && log_success "  Mapping: ${idx}" || log_warn "  Mapping échoué: ${idx}"

        # Re-index existing docs to populate .keyword subfields
        curl -sf -X POST -u "$AUTH" -H "Content-Type: application/json" \
            "${ELASTICSEARCH_URL}/${idx}/_update_by_query?wait_for_completion=false&conflicts=proceed" \
            -d '{"query":{"match_all":{}}}' > /dev/null 2>&1 || true
    done
    log_info "Re-indexation lancée en arrière-plan pour les champs .keyword"
}

# =============================================================================
create_data_views() {
    log_info "Création des data views..."
    for dv_data in \
        "all-logs-index-pattern|recommendation-*-logs-*|Recommendation - All Logs" \
        "api-logs-index-pattern|recommendation-api-logs-*|Recommendation - API Logs" \
        "error-logs-index-pattern|recommendation-errors-*|Recommendation - Error Logs"; do
        IFS='|' read -r id title name <<< "$dv_data"
        curl -sf -X POST -u "$AUTH" -H "kbn-xsrf: true" -H "Content-Type: application/json" \
            "${KIBANA_URL}/api/data_views/data_view" \
            -d "{\"data_view\":{\"id\":\"${id}\",\"title\":\"${title}\",\"timeFieldName\":\"@timestamp\",\"name\":\"${name}\"},\"override\":true}" > /dev/null 2>&1 \
            && log_success "  Data view: ${name}" || log_warn "  Data view ${name}: erreur ou existant"
    done
    # Set default
    curl -sf -X POST -u "$AUTH" -H "kbn-xsrf: true" -H "Content-Type: application/json" \
        "${KIBANA_URL}/api/data_views/default" \
        -d '{"data_view_id":"all-logs-index-pattern","force":true}' > /dev/null 2>&1
}

# =============================================================================
cleanup_old_dashboard() {
    log_info "Nettoyage de l'ancien dashboard..."
    # Delete old dashboard saved object if it exists
    curl -sf -X DELETE -u "$AUTH" -H "kbn-xsrf: true" \
        "${KIBANA_URL}/api/saved_objects/dashboard/api-logs-dashboard" > /dev/null 2>&1 \
        && log_success "  Ancien dashboard supprimé" || log_info "  Pas d'ancien dashboard"
}

# =============================================================================
import_dashboard() {
    log_info "Génération du JSON du dashboard..."
    local json_file="/tmp/api-logs-dashboard.json"

    if ! python3 "${SCRIPT_DIR}/generate-dashboard-ndjson.py" > "$json_file" 2>&1; then
        log_error "Erreur lors de la génération du JSON"
        cat "$json_file"
        return 1
    fi
    log_success "JSON généré ($(wc -c < "$json_file") bytes)"

    # Use direct saved objects API (avoids _import migration issues)
    log_info "Création du dashboard via /api/saved_objects/dashboard/..."
    local response
    response=$(curl -s -w "\n%{http_code}" -X POST \
        -u "$AUTH" \
        -H "kbn-xsrf: true" \
        -H "Content-Type: application/json" \
        "${KIBANA_URL}/api/saved_objects/dashboard/api-logs-dashboard" \
        -d @"$json_file" 2>&1)

    local http_code
    http_code=$(echo "$response" | tail -1)
    local body
    body=$(echo "$response" | head -n -1)

    if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
        log_success "Dashboard créé avec 15 panneaux!"
    elif [ "$http_code" = "409" ]; then
        # Already exists - update it
        log_info "Dashboard existe déjà, mise à jour..."
        response=$(curl -s -w "\n%{http_code}" -X PUT \
            -u "$AUTH" \
            -H "kbn-xsrf: true" \
            -H "Content-Type: application/json" \
            "${KIBANA_URL}/api/saved_objects/dashboard/api-logs-dashboard" \
            -d @"$json_file" 2>&1)
        http_code=$(echo "$response" | tail -1)
        body=$(echo "$response" | head -n -1)
        if [ "$http_code" = "200" ]; then
            log_success "Dashboard mis à jour avec 15 panneaux!"
        else
            log_error "Échec mise à jour (HTTP ${http_code})"
            echo "$body" | head -c 500
        fi
    else
        log_error "Échec création (HTTP ${http_code})"
        echo "$body" | head -c 500
        echo ""
    fi

    rm -f "$json_file"
}

# =============================================================================
main() {
    echo "=============================================="
    echo "  AR_AS - Setup Kibana API Logs Dashboard"
    echo "=============================================="
    echo ""

    wait_for_elasticsearch
    wait_for_kibana
    echo ""

    log_info "Étape 1/5: Template d'index"
    create_index_template
    echo ""

    log_info "Étape 2/5: Mappings des index existants"
    update_existing_mappings
    echo ""

    log_info "Étape 3/5: Data views"
    create_data_views
    echo ""

    log_info "Étape 4/5: Nettoyage"
    cleanup_old_dashboard
    echo ""

    log_info "Étape 5/5: Import du dashboard"
    import_dashboard

    echo ""
    echo "=============================================="
    log_success "Setup terminé!"
    echo ""
    echo "  Dashboard : ${KIBANA_URL}/app/dashboards#/view/api-logs-dashboard"
    echo "  Credentials : ${ELASTIC_USER} / (voir .env)"
    echo ""
    echo "  NOTE: Si les panneaux affichent 'No results', relancez"
    echo "  vos services Docker pour que Logstash réindexe les logs"
    echo "  avec les nouveaux champs (http_method, request_path, etc.)"
    echo "=============================================="
}

main "$@"
