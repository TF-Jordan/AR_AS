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
import_dashboard() {
    log_info "Génération du fichier NDJSON..."
    local ndjson_file="/tmp/api-logs-dashboard.ndjson"

    python3 "${SCRIPT_DIR}/generate-dashboard-ndjson.py" > "$ndjson_file" 2>&1
    if [ $? -ne 0 ]; then
        log_error "Erreur lors de la génération du NDJSON"
        cat "$ndjson_file"
        return 1
    fi

    local line_count
    line_count=$(wc -l < "$ndjson_file")
    log_success "NDJSON généré: ${line_count} objets"

    log_info "Import du dashboard via /api/saved_objects/_import..."
    local response
    response=$(curl -s -w "\n%{http_code}" -X POST \
        -u "$AUTH" \
        -H "kbn-xsrf: true" \
        "${KIBANA_URL}/api/saved_objects/_import?overwrite=true" \
        --form file=@"$ndjson_file" 2>&1)

    local http_code
    http_code=$(echo "$response" | tail -1)
    local body
    body=$(echo "$response" | head -n -1)

    if [ "$http_code" = "200" ]; then
        local success
        success=$(echo "$body" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('success', False))" 2>/dev/null || echo "unknown")

        if [ "$success" = "True" ]; then
            local count
            count=$(echo "$body" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('successCount', 0))" 2>/dev/null || echo "?")
            log_success "Dashboard importé avec succès! (${count} objets)"
        else
            log_warn "Import partiel. Réponse:"
            echo "$body" | python3 -m json.tool 2>/dev/null || echo "$body"
        fi
    else
        log_error "Échec import (HTTP ${http_code})"
        echo "$body" | head -c 500
        echo ""
    fi

    rm -f "$ndjson_file"
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

    log_info "Étape 1/3: Template d'index"
    create_index_template
    echo ""

    log_info "Étape 2/3: Mappings des index existants"
    update_existing_mappings
    echo ""

    log_info "Étape 3/3: Import du dashboard"
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
