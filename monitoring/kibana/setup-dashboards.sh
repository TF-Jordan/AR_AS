#!/bin/bash
# =============================================================================
# Script d'import des dashboards Kibana pour AR_AS
# =============================================================================
# Ce script :
#   1. Attend que Kibana soit prêt
#   2. Crée les index patterns nécessaires
#   3. Importe les dashboards depuis les fichiers NDJSON
#
# Usage:
#   ./setup-dashboards.sh
#   KIBANA_URL=http://localhost:5601 ELASTIC_USER=elastic ELASTIC_PASSWORD=mypass ./setup-dashboards.sh
# =============================================================================

set -euo pipefail

# Configuration
KIBANA_URL="${KIBANA_URL:-http://localhost:5601}"
ELASTIC_USER="${ELASTIC_USER:-elastic}"
ELASTIC_PASSWORD="${ELASTIC_PASSWORD:-Ar@s_Elastic_2024!}"
ELASTICSEARCH_URL="${ELASTICSEARCH_URL:-http://localhost:9200}"
MAX_RETRIES=30
RETRY_INTERVAL=10

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DASHBOARDS_DIR="${SCRIPT_DIR}/dashboards"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# =============================================================================
# Step 1: Wait for Kibana to be ready
# =============================================================================
wait_for_kibana() {
    log_info "Attente de Kibana sur ${KIBANA_URL}..."
    local retries=0
    while [ $retries -lt $MAX_RETRIES ]; do
        if curl -sf -u "${ELASTIC_USER}:${ELASTIC_PASSWORD}" \
            "${KIBANA_URL}/api/status" > /dev/null 2>&1; then
            log_success "Kibana est prêt!"
            return 0
        fi
        retries=$((retries + 1))
        log_warn "Kibana pas encore prêt... tentative ${retries}/${MAX_RETRIES}"
        sleep $RETRY_INTERVAL
    done
    log_error "Kibana n'est pas disponible après ${MAX_RETRIES} tentatives"
    exit 1
}

# =============================================================================
# Step 2: Wait for Elasticsearch to be ready
# =============================================================================
wait_for_elasticsearch() {
    log_info "Attente d'Elasticsearch sur ${ELASTICSEARCH_URL}..."
    local retries=0
    while [ $retries -lt $MAX_RETRIES ]; do
        if curl -sf -u "${ELASTIC_USER}:${ELASTIC_PASSWORD}" \
            "${ELASTICSEARCH_URL}/_cluster/health" > /dev/null 2>&1; then
            log_success "Elasticsearch est prêt!"
            return 0
        fi
        retries=$((retries + 1))
        sleep $RETRY_INTERVAL
    done
    log_error "Elasticsearch n'est pas disponible"
    exit 1
}

# =============================================================================
# Step 3: Create index patterns in Kibana
# =============================================================================
create_index_patterns() {
    log_info "Création des index patterns..."

    local patterns=(
        "recommendation-*-logs-*"
        "recommendation-api-logs-*"
        "recommendation-errors-*"
        "metricbeat-*"
    )

    for pattern in "${patterns[@]}"; do
        log_info "  Création du pattern: ${pattern}"
        local response
        response=$(curl -sf -X POST \
            -u "${ELASTIC_USER}:${ELASTIC_PASSWORD}" \
            -H "kbn-xsrf: true" \
            -H "Content-Type: application/json" \
            "${KIBANA_URL}/api/saved_objects/index-pattern/${pattern}" \
            -d "{
                \"attributes\": {
                    \"title\": \"${pattern}\",
                    \"timeFieldName\": \"@timestamp\"
                }
            }" 2>&1) || true

        if echo "$response" | grep -q '"id"'; then
            log_success "  Index pattern '${pattern}' créé"
        elif echo "$response" | grep -q 'Conflict'; then
            log_warn "  Index pattern '${pattern}' existe déjà"
        else
            log_warn "  Résultat pour '${pattern}': ${response}"
        fi
    done
}

# =============================================================================
# Step 4: Create index template for recommendation logs
# =============================================================================
create_index_template() {
    log_info "Création du template d'index pour les logs de recommandation..."

    curl -sf -X PUT \
        -u "${ELASTIC_USER}:${ELASTIC_PASSWORD}" \
        -H "Content-Type: application/json" \
        "${ELASTICSEARCH_URL}/_index_template/recommendation-logs" \
        -d '{
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
                                "city_name": { "type": "keyword" },
                                "region_name": { "type": "keyword" }
                            }
                        }
                    }
                }
            },
            "priority": 200
        }' > /dev/null 2>&1 && \
        log_success "Template d'index créé" || \
        log_warn "Impossible de créer le template (peut déjà exister)"
}

# =============================================================================
# Step 5: Import NDJSON dashboards
# =============================================================================
import_dashboards() {
    log_info "Import des dashboards depuis ${DASHBOARDS_DIR}..."

    for ndjson_file in "${DASHBOARDS_DIR}"/*.ndjson; do
        if [ ! -f "$ndjson_file" ]; then
            log_warn "Aucun fichier NDJSON trouvé"
            return
        fi

        local filename
        filename=$(basename "$ndjson_file")
        log_info "  Import de: ${filename}"

        local response
        response=$(curl -sf -X POST \
            -u "${ELASTIC_USER}:${ELASTIC_PASSWORD}" \
            -H "kbn-xsrf: true" \
            "${KIBANA_URL}/api/saved_objects/_import?overwrite=true" \
            --form file=@"${ndjson_file}" 2>&1) || true

        if echo "$response" | grep -q '"success":true'; then
            local count
            count=$(echo "$response" | grep -o '"successCount":[0-9]*' | grep -o '[0-9]*')
            log_success "  ${filename}: ${count:-?} objets importés"
        elif echo "$response" | grep -q '"success":false'; then
            local errors
            errors=$(echo "$response" | grep -o '"errors":\[.*\]' | head -c 200)
            log_warn "  ${filename}: Import partiel - ${errors}"
        else
            log_warn "  ${filename}: Résultat inattendu - ${response:0:200}"
        fi
    done
}

# =============================================================================
# Step 6: Set default index pattern
# =============================================================================
set_default_index_pattern() {
    log_info "Configuration du pattern d'index par défaut..."
    curl -sf -X POST \
        -u "${ELASTIC_USER}:${ELASTIC_PASSWORD}" \
        -H "kbn-xsrf: true" \
        -H "Content-Type: application/json" \
        "${KIBANA_URL}/api/kibana/settings" \
        -d '{"changes": {"defaultIndex": "recommendation-*-logs-*"}}' \
        > /dev/null 2>&1 && \
        log_success "Index pattern par défaut configuré" || \
        log_warn "Impossible de configurer l'index pattern par défaut"
}

# =============================================================================
# Main
# =============================================================================
main() {
    echo "=============================================="
    echo "  AR_AS - Setup Kibana Dashboards"
    echo "=============================================="
    echo ""

    wait_for_elasticsearch
    wait_for_kibana
    create_index_template
    create_index_patterns
    import_dashboards
    set_default_index_pattern

    echo ""
    echo "=============================================="
    log_success "Setup terminé!"
    echo ""
    echo "  Accédez aux dashboards:"
    echo "    ${KIBANA_URL}/app/dashboards"
    echo ""
    echo "  Credentials:"
    echo "    User: ${ELASTIC_USER}"
    echo "    Pass: (configuré dans .env)"
    echo "=============================================="
}

main "$@"
