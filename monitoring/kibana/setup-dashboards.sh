#!/bin/bash
# =============================================================================
# Script de création du Dashboard API Logs pour Kibana 8.11
# =============================================================================
# Utilise des panneaux "by-value" (inline) pour éviter les problèmes
# de mapping avec les objets lens séparés.
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
DV_ID="all-logs-index-pattern"
DV_TITLE="recommendation-*-logs-*"

# =============================================================================
wait_for_elasticsearch() {
    log_info "Attente d'Elasticsearch..."
    local r=0
    while [ $r -lt $MAX_RETRIES ]; do
        curl -sf -u "$AUTH" "${ELASTICSEARCH_URL}/_cluster/health" > /dev/null 2>&1 && { log_success "Elasticsearch prêt!"; return 0; }
        r=$((r + 1)); sleep $RETRY_INTERVAL
    done
    log_error "Elasticsearch non disponible"; exit 1
}

wait_for_kibana() {
    log_info "Attente de Kibana..."
    local r=0
    while [ $r -lt $MAX_RETRIES ]; do
        curl -sf -u "$AUTH" "${KIBANA_URL}/api/status" > /dev/null 2>&1 && { log_success "Kibana prêt!"; return 0; }
        r=$((r + 1)); sleep $RETRY_INTERVAL
    done
    log_error "Kibana non disponible"; exit 1
}

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
update_existing_mappings() {
    log_info "Mise à jour des mappings des index existants..."
    # Get all existing recommendation log indices
    local indices
    indices=$(curl -sf -u "$AUTH" "${ELASTICSEARCH_URL}/_cat/indices/recommendation-*-logs-*?h=index" 2>/dev/null || echo "")
    if [ -z "$indices" ]; then
        log_warn "Aucun index existant trouvé"
        return 0
    fi
    for idx in $indices; do
        curl -sf -X PUT -u "$AUTH" -H "Content-Type: application/json" \
            "${ELASTICSEARCH_URL}/${idx}/_mapping" \
            -d '{
                "properties": {
                    "level": { "type": "text", "fields": { "keyword": { "type": "keyword" } } },
                    "service_type": { "type": "text", "fields": { "keyword": { "type": "keyword" } } },
                    "http_method": { "type": "text", "fields": { "keyword": { "type": "keyword" } } },
                    "request_path": { "type": "text", "fields": { "keyword": { "type": "keyword" } } },
                    "response_category": { "type": "text", "fields": { "keyword": { "type": "keyword" } } },
                    "request_id": { "type": "text", "fields": { "keyword": { "type": "keyword" } } }
                }
            }' > /dev/null 2>&1 \
            && log_success "  Mapping mis à jour: ${idx}" || log_warn "  Mapping échoué: ${idx}"
        # Refresh the .keyword subfields on existing docs
        curl -sf -X POST -u "$AUTH" -H "Content-Type: application/json" \
            "${ELASTICSEARCH_URL}/${idx}/_update_by_query?wait_for_completion=false&conflicts=proceed" \
            -d '{"query":{"match_all":{}}}' > /dev/null 2>&1 || true
    done
    log_info "Re-indexation en arrière-plan lancée pour les champs .keyword"
}

create_data_views() {
    log_info "Création des data views..."
    for dv_data in \
        "all-logs-index-pattern|recommendation-*-logs-*|Recommendation - All Logs" \
        "api-logs-index-pattern|recommendation-api-logs-*|Recommendation - API Logs" \
        "error-logs-index-pattern|recommendation-errors-*|Recommendation - Error Logs" \
        "metricbeat-index-pattern|metricbeat-*|Metricbeat"; do
        IFS='|' read -r id title name <<< "$dv_data"
        curl -sf -X POST -u "$AUTH" -H "kbn-xsrf: true" -H "Content-Type: application/json" \
            "${KIBANA_URL}/api/data_views/data_view" \
            -d "{\"data_view\":{\"id\":\"${id}\",\"title\":\"${title}\",\"timeFieldName\":\"@timestamp\",\"name\":\"${name}\"},\"override\":true}" > /dev/null 2>&1 \
            && log_success "  ${name}" || log_warn "  ${name}: erreur"
    done
    curl -sf -X POST -u "$AUTH" -H "kbn-xsrf: true" -H "Content-Type: application/json" \
        "${KIBANA_URL}/api/data_views/default" \
        -d '{"data_view_id":"all-logs-index-pattern","force":true}' > /dev/null 2>&1

    # Refresh field list for the main data view so Kibana sees .keyword subfields
    log_info "Rafraîchissement des champs du data view..."
    curl -sf -X POST -u "$AUTH" -H "kbn-xsrf: true" -H "Content-Type: application/json" \
        "${KIBANA_URL}/api/data_views/data_view/${DV_ID}/runtime_field" \
        -d '{}' > /dev/null 2>&1 || true
    # Force refresh by re-fetching fields
    curl -sf -u "$AUTH" -H "kbn-xsrf: true" \
        "${KIBANA_URL}/api/data_views/data_view/${DV_ID}" > /dev/null 2>&1 || true
}

# =============================================================================
# Build dashboard with by-value (inline) panels
# No separate lens saved objects needed!
# =============================================================================
create_dashboard() {
    log_info "Création du dashboard avec panneaux inline (by-value)..."

    # Helper to build an inline metric panel
    # $1=panelId $2=x $3=y $4=w $5=h $6=title $7=sourceField $8=operation $9=query ${10}=subtitle ${11}=extra_params
    build_metric_panel() {
        local pid="$1" x="$2" y="$3" w="$4" h="$5" title="$6" field="$7" op="$8" query="$9" subtitle="${10}" extra="${11:-}"
        local col_def
        if [ "$op" = "count" ]; then
            col_def="{\"label\":\"${title}\",\"dataType\":\"number\",\"operationType\":\"count\",\"isBucketed\":false,\"scale\":\"ratio\",\"sourceField\":\"___records___\"}"
        elif [ "$op" = "average" ]; then
            col_def="{\"label\":\"${title}\",\"dataType\":\"number\",\"operationType\":\"average\",\"isBucketed\":false,\"scale\":\"ratio\",\"sourceField\":\"${field}\"}"
        elif [ "$op" = "percentile" ]; then
            col_def="{\"label\":\"${title}\",\"dataType\":\"number\",\"operationType\":\"percentile\",\"isBucketed\":false,\"scale\":\"ratio\",\"sourceField\":\"${field}\",\"params\":{\"percentile\":95}}"
        fi

        cat <<PANEL_EOF
{
  "version":"8.11.0",
  "type":"lens",
  "gridData":{"x":${x},"y":${y},"w":${w},"h":${h},"i":"${pid}"},
  "panelIndex":"${pid}",
  "title":"${title}",
  "embeddableConfig":{
    "attributes":{
      "title":"${title}",
      "visualizationType":"lnsMetric",
      "state":{
        "datasourceStates":{"formBased":{"layers":{"layer1":{"columns":{"col1":${col_def}},"columnOrder":["col1"],"incompleteColumns":{}}}}},
        "visualization":{"layerId":"layer1","accessor":"col1","layerType":"data","subtitle":"${subtitle}"},
        "query":{"query":"${query}","language":"kuery"},
        "filters":[]
      },
      "references":[{"type":"index-pattern","id":"${DV_ID}","name":"indexpattern-datasource-layer-layer1"}]
    },
    "enhancements":{}
  }
}
PANEL_EOF
    }

    # Build the panels JSON array
    local panels=""

    # --- ROW 1: KPI Metrics ---
    local p1=$(build_metric_panel "p1" 0 0 12 8 "Total Requêtes API" "" "count" "service_type: api" "Dernières 24h")
    local p2=$(build_metric_panel "p2" 12 0 12 8 "Erreurs (4xx+5xx)" "" "count" "http_status >= 400" "Erreurs")
    local p3=$(build_metric_panel "p3" 24 0 12 8 "Temps Moyen (ms)" "duration_ms" "average" "service_type: api" "Moyenne")
    local p4=$(build_metric_panel "p4" 36 0 12 8 "P95 (ms)" "duration_ms" "percentile" "service_type: api" "Percentile 95")

    # --- ROW 2: Requests over time (bar chart) ---
    local p5=$(cat <<'P5_EOF'
{
  "version":"8.11.0","type":"lens",
  "gridData":{"x":0,"y":8,"w":32,"h":14,"i":"p5"},"panelIndex":"p5",
  "title":"Requêtes API dans le Temps",
  "embeddableConfig":{
    "attributes":{
      "title":"Requêtes API dans le Temps","visualizationType":"lnsXY",
      "state":{
        "datasourceStates":{"formBased":{"layers":{"layer1":{"columns":{
          "col1":{"label":"Timestamp","dataType":"date","operationType":"date_histogram","isBucketed":true,"scale":"interval","sourceField":"@timestamp","params":{"interval":"auto"}},
          "col2":{"label":"Requêtes","dataType":"number","operationType":"count","isBucketed":false,"scale":"ratio","sourceField":"___records___"}
        },"columnOrder":["col1","col2"],"incompleteColumns":{}}}}},
        "visualization":{"legend":{"isVisible":true,"position":"bottom"},"preferredSeriesType":"bar","layers":[{"layerId":"layer1","accessors":["col2"],"seriesType":"bar","layerType":"data","xAccessor":"col1"}],"yTitle":"Requêtes","xTitle":"Temps"},
        "query":{"query":"service_type: api","language":"kuery"},"filters":[]
      },
      "references":[{"type":"index-pattern","id":"DV_ID_PLACEHOLDER","name":"indexpattern-datasource-layer-layer1"}]
    },"enhancements":{}
  }
}
P5_EOF
)
    p5="${p5//DV_ID_PLACEHOLDER/$DV_ID}"

    # --- Distribution codes HTTP (donut) ---
    local p6=$(cat <<'P6_EOF'
{
  "version":"8.11.0","type":"lens",
  "gridData":{"x":32,"y":8,"w":16,"h":14,"i":"p6"},"panelIndex":"p6",
  "title":"Distribution Codes HTTP",
  "embeddableConfig":{
    "attributes":{
      "title":"Distribution Codes HTTP","visualizationType":"lnsPie",
      "state":{
        "datasourceStates":{"formBased":{"layers":{"layer1":{"columns":{
          "col1":{"label":"Status","dataType":"number","operationType":"terms","isBucketed":true,"scale":"ordinal","sourceField":"http_status","params":{"size":10,"orderBy":{"type":"column","columnId":"col2"},"orderDirection":"desc"}},
          "col2":{"label":"Count","dataType":"number","operationType":"count","isBucketed":false,"scale":"ratio","sourceField":"___records___"}
        },"columnOrder":["col1","col2"],"incompleteColumns":{}}}}},
        "visualization":{"shape":"donut","layers":[{"layerId":"layer1","primaryGroups":["col1"],"metrics":["col2"],"numberDisplay":"percent","categoryDisplay":"default","legendDisplay":"default","layerType":"data"}]},
        "query":{"query":"http_status: *","language":"kuery"},"filters":[]
      },
      "references":[{"type":"index-pattern","id":"DV_ID_PLACEHOLDER","name":"indexpattern-datasource-layer-layer1"}]
    },"enhancements":{}
  }
}
P6_EOF
)
    p6="${p6//DV_ID_PLACEHOLDER/$DV_ID}"

    # --- Response time over time (line) ---
    local p7=$(cat <<'P7_EOF'
{
  "version":"8.11.0","type":"lens",
  "gridData":{"x":0,"y":22,"w":32,"h":14,"i":"p7"},"panelIndex":"p7",
  "title":"Temps de Réponse dans le Temps",
  "embeddableConfig":{
    "attributes":{
      "title":"Temps de Réponse","visualizationType":"lnsXY",
      "state":{
        "datasourceStates":{"formBased":{"layers":{"layer1":{"columns":{
          "col1":{"label":"Timestamp","dataType":"date","operationType":"date_histogram","isBucketed":true,"scale":"interval","sourceField":"@timestamp","params":{"interval":"auto"}},
          "col2":{"label":"Moyenne (ms)","dataType":"number","operationType":"average","isBucketed":false,"scale":"ratio","sourceField":"duration_ms"},
          "col3":{"label":"P95 (ms)","dataType":"number","operationType":"percentile","isBucketed":false,"scale":"ratio","sourceField":"duration_ms","params":{"percentile":95}}
        },"columnOrder":["col1","col2","col3"],"incompleteColumns":{}}}}},
        "visualization":{"legend":{"isVisible":true,"position":"bottom"},"preferredSeriesType":"line","layers":[{"layerId":"layer1","accessors":["col2","col3"],"seriesType":"line","layerType":"data","xAccessor":"col1"}],"yTitle":"ms","xTitle":"Temps"},
        "query":{"query":"service_type: api AND duration_ms: *","language":"kuery"},"filters":[]
      },
      "references":[{"type":"index-pattern","id":"DV_ID_PLACEHOLDER","name":"indexpattern-datasource-layer-layer1"}]
    },"enhancements":{}
  }
}
P7_EOF
)
    p7="${p7//DV_ID_PLACEHOLDER/$DV_ID}"

    # --- Response category (pie) ---
    local p8=$(cat <<'P8_EOF'
{
  "version":"8.11.0","type":"lens",
  "gridData":{"x":32,"y":22,"w":16,"h":14,"i":"p8"},"panelIndex":"p8",
  "title":"Catégorie Temps de Réponse",
  "embeddableConfig":{
    "attributes":{
      "title":"Catégorie Temps de Réponse","visualizationType":"lnsPie",
      "state":{
        "datasourceStates":{"formBased":{"layers":{"layer1":{"columns":{
          "col1":{"label":"Catégorie","dataType":"string","operationType":"terms","isBucketed":true,"scale":"ordinal","sourceField":"response_category.keyword","params":{"size":5,"orderBy":{"type":"column","columnId":"col2"},"orderDirection":"desc"}},
          "col2":{"label":"Count","dataType":"number","operationType":"count","isBucketed":false,"scale":"ratio","sourceField":"___records___"}
        },"columnOrder":["col1","col2"],"incompleteColumns":{}}}}},
        "visualization":{"shape":"pie","layers":[{"layerId":"layer1","primaryGroups":["col1"],"metrics":["col2"],"numberDisplay":"percent","categoryDisplay":"default","legendDisplay":"default","layerType":"data"}]},
        "query":{"query":"response_category: *","language":"kuery"},"filters":[]
      },
      "references":[{"type":"index-pattern","id":"DV_ID_PLACEHOLDER","name":"indexpattern-datasource-layer-layer1"}]
    },"enhancements":{}
  }
}
P8_EOF
)
    p8="${p8//DV_ID_PLACEHOLDER/$DV_ID}"

    # --- Top endpoints (table) ---
    local p9=$(cat <<'P9_EOF'
{
  "version":"8.11.0","type":"lens",
  "gridData":{"x":0,"y":36,"w":48,"h":14,"i":"p9"},"panelIndex":"p9",
  "title":"Top 10 Endpoints",
  "embeddableConfig":{
    "attributes":{
      "title":"Top 10 Endpoints","visualizationType":"lnsDatatable",
      "state":{
        "datasourceStates":{"formBased":{"layers":{"layer1":{"columns":{
          "col1":{"label":"Endpoint","dataType":"string","operationType":"terms","isBucketed":true,"scale":"ordinal","sourceField":"request_path.keyword","params":{"size":10,"orderBy":{"type":"column","columnId":"col2"},"orderDirection":"desc"}},
          "col2":{"label":"Requêtes","dataType":"number","operationType":"count","isBucketed":false,"scale":"ratio","sourceField":"___records___"},
          "col3":{"label":"Temps Moyen (ms)","dataType":"number","operationType":"average","isBucketed":false,"scale":"ratio","sourceField":"duration_ms"}
        },"columnOrder":["col1","col2","col3"],"incompleteColumns":{}}}}},
        "visualization":{"layerId":"layer1","layerType":"data","columns":[{"columnId":"col1","width":300},{"columnId":"col2","alignment":"center"},{"columnId":"col3","alignment":"center"}],"paging":{"size":10,"enabled":true}},
        "query":{"query":"request_path: * AND service_type: api","language":"kuery"},"filters":[]
      },
      "references":[{"type":"index-pattern","id":"DV_ID_PLACEHOLDER","name":"indexpattern-datasource-layer-layer1"}]
    },"enhancements":{}
  }
}
P9_EOF
)
    p9="${p9//DV_ID_PLACEHOLDER/$DV_ID}"

    # --- By method (stacked bar) ---
    local p10=$(cat <<'P10_EOF'
{
  "version":"8.11.0","type":"lens",
  "gridData":{"x":0,"y":50,"w":24,"h":14,"i":"p10"},"panelIndex":"p10",
  "title":"Requêtes par Méthode HTTP",
  "embeddableConfig":{
    "attributes":{
      "title":"Par Méthode HTTP","visualizationType":"lnsXY",
      "state":{
        "datasourceStates":{"formBased":{"layers":{"layer1":{"columns":{
          "col1":{"label":"Timestamp","dataType":"date","operationType":"date_histogram","isBucketed":true,"scale":"interval","sourceField":"@timestamp","params":{"interval":"auto"}},
          "col2":{"label":"Méthode","dataType":"string","operationType":"terms","isBucketed":true,"scale":"ordinal","sourceField":"http_method.keyword","params":{"size":6,"orderBy":{"type":"column","columnId":"col3"},"orderDirection":"desc"}},
          "col3":{"label":"Count","dataType":"number","operationType":"count","isBucketed":false,"scale":"ratio","sourceField":"___records___"}
        },"columnOrder":["col1","col2","col3"],"incompleteColumns":{}}}}},
        "visualization":{"legend":{"isVisible":true,"position":"right"},"preferredSeriesType":"bar_stacked","layers":[{"layerId":"layer1","accessors":["col3"],"seriesType":"bar_stacked","layerType":"data","xAccessor":"col1","splitAccessor":"col2"}],"yTitle":"Requêtes"},
        "query":{"query":"http_method: *","language":"kuery"},"filters":[]
      },
      "references":[{"type":"index-pattern","id":"DV_ID_PLACEHOLDER","name":"indexpattern-datasource-layer-layer1"}]
    },"enhancements":{}
  }
}
P10_EOF
)
    p10="${p10//DV_ID_PLACEHOLDER/$DV_ID}"

    # --- By service (area stacked) ---
    local p11=$(cat <<'P11_EOF'
{
  "version":"8.11.0","type":"lens",
  "gridData":{"x":24,"y":50,"w":24,"h":14,"i":"p11"},"panelIndex":"p11",
  "title":"Logs par Service",
  "embeddableConfig":{
    "attributes":{
      "title":"Logs par Service","visualizationType":"lnsXY",
      "state":{
        "datasourceStates":{"formBased":{"layers":{"layer1":{"columns":{
          "col1":{"label":"Timestamp","dataType":"date","operationType":"date_histogram","isBucketed":true,"scale":"interval","sourceField":"@timestamp","params":{"interval":"auto"}},
          "col2":{"label":"Service","dataType":"string","operationType":"terms","isBucketed":true,"scale":"ordinal","sourceField":"service_type.keyword","params":{"size":5,"orderBy":{"type":"column","columnId":"col3"},"orderDirection":"desc"}},
          "col3":{"label":"Count","dataType":"number","operationType":"count","isBucketed":false,"scale":"ratio","sourceField":"___records___"}
        },"columnOrder":["col1","col2","col3"],"incompleteColumns":{}}}}},
        "visualization":{"legend":{"isVisible":true,"position":"right"},"preferredSeriesType":"area_stacked","layers":[{"layerId":"layer1","accessors":["col3"],"seriesType":"area_stacked","layerType":"data","xAccessor":"col1","splitAccessor":"col2"}],"yTitle":"Logs"},
        "query":{"query":"","language":"kuery"},"filters":[]
      },
      "references":[{"type":"index-pattern","id":"DV_ID_PLACEHOLDER","name":"indexpattern-datasource-layer-layer1"}]
    },"enhancements":{}
  }
}
P11_EOF
)
    p11="${p11//DV_ID_PLACEHOLDER/$DV_ID}"

    # --- By log level (stacked bar) ---
    local p12=$(cat <<'P12_EOF'
{
  "version":"8.11.0","type":"lens",
  "gridData":{"x":0,"y":64,"w":48,"h":12,"i":"p12"},"panelIndex":"p12",
  "title":"Logs par Niveau",
  "embeddableConfig":{
    "attributes":{
      "title":"Logs par Niveau","visualizationType":"lnsXY",
      "state":{
        "datasourceStates":{"formBased":{"layers":{"layer1":{"columns":{
          "col1":{"label":"Timestamp","dataType":"date","operationType":"date_histogram","isBucketed":true,"scale":"interval","sourceField":"@timestamp","params":{"interval":"auto"}},
          "col2":{"label":"Level","dataType":"string","operationType":"terms","isBucketed":true,"scale":"ordinal","sourceField":"level.keyword","params":{"size":5,"orderBy":{"type":"column","columnId":"col3"},"orderDirection":"desc"}},
          "col3":{"label":"Count","dataType":"number","operationType":"count","isBucketed":false,"scale":"ratio","sourceField":"___records___"}
        },"columnOrder":["col1","col2","col3"],"incompleteColumns":{}}}}},
        "visualization":{"legend":{"isVisible":true,"position":"right"},"preferredSeriesType":"bar_stacked","layers":[{"layerId":"layer1","accessors":["col3"],"seriesType":"bar_stacked","layerType":"data","xAccessor":"col1","splitAccessor":"col2"}],"yTitle":"Logs"},
        "query":{"query":"","language":"kuery"},"filters":[]
      },
      "references":[{"type":"index-pattern","id":"DV_ID_PLACEHOLDER","name":"indexpattern-datasource-layer-layer1"}]
    },"enhancements":{}
  }
}
P12_EOF
)
    p12="${p12//DV_ID_PLACEHOLDER/$DV_ID}"

    # --- Recent errors table ---
    local p13=$(cat <<'P13_EOF'
{
  "version":"8.11.0","type":"lens",
  "gridData":{"x":0,"y":76,"w":24,"h":14,"i":"p13"},"panelIndex":"p13",
  "title":"Erreurs Récentes",
  "embeddableConfig":{
    "attributes":{
      "title":"Erreurs Récentes","visualizationType":"lnsDatatable",
      "state":{
        "datasourceStates":{"formBased":{"layers":{"layer1":{"columns":{
          "col1":{"label":"Timestamp","dataType":"date","operationType":"date_histogram","isBucketed":true,"scale":"interval","sourceField":"@timestamp","params":{"interval":"1h"}},
          "col2":{"label":"Endpoint","dataType":"string","operationType":"terms","isBucketed":true,"scale":"ordinal","sourceField":"request_path.keyword","params":{"size":20,"orderBy":{"type":"column","columnId":"col3"},"orderDirection":"desc"}},
          "col3":{"label":"Count","dataType":"number","operationType":"count","isBucketed":false,"scale":"ratio","sourceField":"___records___"}
        },"columnOrder":["col1","col2","col3"],"incompleteColumns":{}}}}},
        "visualization":{"layerId":"layer1","layerType":"data","columns":[{"columnId":"col1"},{"columnId":"col2","width":250},{"columnId":"col3","alignment":"center"}],"paging":{"size":10,"enabled":true}},
        "query":{"query":"http_status >= 400","language":"kuery"},"filters":[]
      },
      "references":[{"type":"index-pattern","id":"DV_ID_PLACEHOLDER","name":"indexpattern-datasource-layer-layer1"}]
    },"enhancements":{}
  }
}
P13_EOF
)
    p13="${p13//DV_ID_PLACEHOLDER/$DV_ID}"

    # --- Slow requests table ---
    local p14=$(cat <<'P14_EOF'
{
  "version":"8.11.0","type":"lens",
  "gridData":{"x":24,"y":76,"w":24,"h":14,"i":"p14"},"panelIndex":"p14",
  "title":"Requêtes Lentes (>500ms)",
  "embeddableConfig":{
    "attributes":{
      "title":"Requêtes Lentes","visualizationType":"lnsDatatable",
      "state":{
        "datasourceStates":{"formBased":{"layers":{"layer1":{"columns":{
          "col1":{"label":"Endpoint","dataType":"string","operationType":"terms","isBucketed":true,"scale":"ordinal","sourceField":"request_path.keyword","params":{"size":15,"orderBy":{"type":"column","columnId":"col2"},"orderDirection":"desc"}},
          "col2":{"label":"Temps Moyen (ms)","dataType":"number","operationType":"average","isBucketed":false,"scale":"ratio","sourceField":"duration_ms"},
          "col3":{"label":"Count","dataType":"number","operationType":"count","isBucketed":false,"scale":"ratio","sourceField":"___records___"}
        },"columnOrder":["col1","col2","col3"],"incompleteColumns":{}}}}},
        "visualization":{"layerId":"layer1","layerType":"data","columns":[{"columnId":"col1","width":250},{"columnId":"col2","alignment":"center"},{"columnId":"col3","alignment":"center"}],"paging":{"size":10,"enabled":true}},
        "query":{"query":"duration_ms > 500","language":"kuery"},"filters":[]
      },
      "references":[{"type":"index-pattern","id":"DV_ID_PLACEHOLDER","name":"indexpattern-datasource-layer-layer1"}]
    },"enhancements":{}
  }
}
P14_EOF
)
    p14="${p14//DV_ID_PLACEHOLDER/$DV_ID}"

    # --- Correlation ID tracking table ---
    local p15=$(cat <<'P15_EOF'
{
  "version":"8.11.0","type":"lens",
  "gridData":{"x":0,"y":90,"w":48,"h":14,"i":"p15"},"panelIndex":"p15",
  "title":"Suivi par Correlation ID",
  "embeddableConfig":{
    "attributes":{
      "title":"Correlation ID","visualizationType":"lnsDatatable",
      "state":{
        "datasourceStates":{"formBased":{"layers":{"layer1":{"columns":{
          "col1":{"label":"Request ID","dataType":"string","operationType":"terms","isBucketed":true,"scale":"ordinal","sourceField":"request_id.keyword","params":{"size":20,"orderBy":{"type":"column","columnId":"col3"},"orderDirection":"desc"}},
          "col2":{"label":"Service","dataType":"string","operationType":"terms","isBucketed":true,"scale":"ordinal","sourceField":"service_type.keyword","params":{"size":5,"orderBy":{"type":"column","columnId":"col3"},"orderDirection":"desc"}},
          "col3":{"label":"Logs","dataType":"number","operationType":"count","isBucketed":false,"scale":"ratio","sourceField":"___records___"},
          "col4":{"label":"Durée (ms)","dataType":"number","operationType":"average","isBucketed":false,"scale":"ratio","sourceField":"duration_ms"}
        },"columnOrder":["col1","col2","col3","col4"],"incompleteColumns":{}}}}},
        "visualization":{"layerId":"layer1","layerType":"data","columns":[{"columnId":"col1","width":300},{"columnId":"col2","alignment":"center"},{"columnId":"col3","alignment":"center"},{"columnId":"col4","alignment":"center"}],"paging":{"size":10,"enabled":true}},
        "query":{"query":"request_id: *","language":"kuery"},"filters":[]
      },
      "references":[{"type":"index-pattern","id":"DV_ID_PLACEHOLDER","name":"indexpattern-datasource-layer-layer1"}]
    },"enhancements":{}
  }
}
P15_EOF
)
    p15="${p15//DV_ID_PLACEHOLDER/$DV_ID}"

    # Combine all panels into JSON array
    local panels_json
    panels_json=$(echo "[${p1},${p2},${p3},${p4},${p5},${p6},${p7},${p8},${p9},${p10},${p11},${p12},${p13},${p14},${p15}]" | python3 -c "import sys,json; json.dump(json.load(sys.stdin),sys.stdout,separators=(',',':'))")

    # Escape for embedding in JSON string
    local panels_escaped
    panels_escaped=$(echo "$panels_json" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read().strip()))")
    # Remove outer quotes from json.dumps
    panels_escaped="${panels_escaped:1:-1}"

    # Create the dashboard via API
    local body
    body=$(cat <<DASH_EOF
{
    "attributes": {
        "title": "API Logs Dashboard - AR_AS",
        "description": "Dashboard complet - 15 panneaux : KPIs, requêtes, temps de réponse, erreurs, endpoints, méthodes HTTP, services, niveaux de log, et corrélation",
        "panelsJSON": "${panels_escaped}",
        "optionsJSON": "{\"useMargins\":true,\"syncColors\":true,\"syncCursor\":true,\"syncTooltips\":false,\"hidePanelTitles\":false}",
        "timeRestore": true,
        "timeTo": "now",
        "timeFrom": "now-24h",
        "refreshInterval": {"pause":false,"value":30000},
        "kibanaSavedObjectMeta": {
            "searchSourceJSON": "{\"query\":{\"query\":\"\",\"language\":\"kuery\"},\"filter\":[]}"
        }
    },
    "references": [
        {"type":"index-pattern","id":"${DV_ID}","name":"indexpattern-datasource-layer-layer1"}
    ]
}
DASH_EOF
)

    # Delete old dashboard first
    curl -sf -X DELETE -u "$AUTH" -H "kbn-xsrf: true" \
        "${KIBANA_URL}/api/saved_objects/dashboard/api-logs-dashboard" > /dev/null 2>&1 || true

    local response
    response=$(curl -s -w "\n%{http_code}" -X POST \
        -u "$AUTH" \
        -H "kbn-xsrf: true" \
        -H "Content-Type: application/json" \
        "${KIBANA_URL}/api/saved_objects/dashboard/api-logs-dashboard" \
        -d "$body" 2>&1)

    local http_code
    http_code=$(echo "$response" | tail -1)

    if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
        log_success "Dashboard créé avec 15 panneaux inline!"
    else
        log_error "Échec création dashboard (HTTP ${http_code})"
        echo "$(echo "$response" | head -n -1 | head -c 300)"
    fi
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
    create_index_template
    echo ""
    update_existing_mappings
    echo ""
    create_data_views
    echo ""
    create_dashboard

    echo ""
    echo "=============================================="
    log_success "Setup terminé!"
    echo ""
    echo "  Dashboard : ${KIBANA_URL}/app/dashboards#/view/api-logs-dashboard"
    echo "  Credentials : ${ELASTIC_USER} / (voir .env)"
    echo "=============================================="
}

main "$@"
