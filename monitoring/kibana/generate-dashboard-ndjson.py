#!/usr/bin/env python3
"""
Generate Kibana 8.11 NDJSON for API Logs Dashboard.

Produces a valid NDJSON file for import via:
  POST /api/saved_objects/_import?overwrite=true

Usage:
  python3 generate-dashboard-ndjson.py > dashboard.ndjson
"""

import json
import sys

DV_ID = "all-logs-index-pattern"
DV_TITLE = "recommendation-*-logs-*"
DASHBOARD_ID = "api-logs-dashboard"


def make_ref(panel_id: str, layer_id: str = "layer1") -> dict:
    """Dashboard-level reference for a by-value panel."""
    return {
        "type": "index-pattern",
        "id": DV_ID,
        "name": f"{panel_id}:indexpattern-datasource-layer-{layer_id}",
    }


def panel_ref(layer_id: str = "layer1") -> list:
    """Panel-level (inside embeddableConfig.attributes) references."""
    return [
        {
            "type": "index-pattern",
            "id": DV_ID,
            "name": f"indexpattern-datasource-layer-{layer_id}",
        }
    ]


def metric_panel(
    panel_id, x, y, w, h, title, operation, source_field="___records___",
    query="", subtitle="", params=None
):
    """Build a lnsMetric panel."""
    col = {
        "label": title,
        "dataType": "number",
        "operationType": operation,
        "isBucketed": False,
        "scale": "ratio",
        "sourceField": source_field,
    }
    if params:
        col["params"] = params

    return {
        "type": "lens",
        "gridData": {"x": x, "y": y, "w": w, "h": h, "i": panel_id},
        "panelIndex": panel_id,
        "title": title,
        "embeddableConfig": {
            "attributes": {
                "title": title,
                "visualizationType": "lnsMetric",
                "type": "lens",
                "references": panel_ref(),
                "state": {
                    "datasourceStates": {
                        "formBased": {
                            "layers": {
                                "layer1": {
                                    "columns": {"col1": col},
                                    "columnOrder": ["col1"],
                                    "incompleteColumns": {},
                                }
                            }
                        }
                    },
                    "visualization": {
                        "layerId": "layer1",
                        "accessor": "col1",
                        "layerType": "data",
                        "subtitle": subtitle,
                    },
                    "query": {"query": query, "language": "kuery"},
                    "filters": [],
                },
            },
            "enhancements": {},
        },
    }


def xy_panel(
    panel_id, x, y, w, h, title, columns, series_type,
    query="", x_accessor="col_x", y_accessors=None, split_accessor=None,
    y_title="", x_title=""
):
    """Build a lnsXY panel (bar, line, area)."""
    if y_accessors is None:
        y_accessors = ["col_y"]

    layer_config = {
        "layerId": "layer1",
        "accessors": y_accessors,
        "seriesType": series_type,
        "layerType": "data",
        "xAccessor": x_accessor,
    }
    if split_accessor:
        layer_config["splitAccessor"] = split_accessor

    viz = {
        "legend": {"isVisible": True, "position": "right" if split_accessor else "bottom"},
        "preferredSeriesType": series_type,
        "layers": [layer_config],
    }
    if y_title:
        viz["yTitle"] = y_title
    if x_title:
        viz["xTitle"] = x_title

    return {
        "type": "lens",
        "gridData": {"x": x, "y": y, "w": w, "h": h, "i": panel_id},
        "panelIndex": panel_id,
        "title": title,
        "embeddableConfig": {
            "attributes": {
                "title": title,
                "visualizationType": "lnsXY",
                "type": "lens",
                "references": panel_ref(),
                "state": {
                    "datasourceStates": {
                        "formBased": {
                            "layers": {
                                "layer1": {
                                    "columns": columns,
                                    "columnOrder": list(columns.keys()),
                                    "incompleteColumns": {},
                                }
                            }
                        }
                    },
                    "visualization": viz,
                    "query": {"query": query, "language": "kuery"},
                    "filters": [],
                },
            },
            "enhancements": {},
        },
    }


def pie_panel(panel_id, x, y, w, h, title, columns, shape="donut", query=""):
    """Build a lnsPie panel."""
    return {
        "type": "lens",
        "gridData": {"x": x, "y": y, "w": w, "h": h, "i": panel_id},
        "panelIndex": panel_id,
        "title": title,
        "embeddableConfig": {
            "attributes": {
                "title": title,
                "visualizationType": "lnsPie",
                "type": "lens",
                "references": panel_ref(),
                "state": {
                    "datasourceStates": {
                        "formBased": {
                            "layers": {
                                "layer1": {
                                    "columns": columns,
                                    "columnOrder": list(columns.keys()),
                                    "incompleteColumns": {},
                                }
                            }
                        }
                    },
                    "visualization": {
                        "shape": shape,
                        "layers": [
                            {
                                "layerId": "layer1",
                                "primaryGroups": ["col_bucket"],
                                "metrics": ["col_metric"],
                                "numberDisplay": "percent",
                                "categoryDisplay": "default",
                                "legendDisplay": "default",
                                "layerType": "data",
                            }
                        ],
                    },
                    "query": {"query": query, "language": "kuery"},
                    "filters": [],
                },
            },
            "enhancements": {},
        },
    }


def table_panel(panel_id, x, y, w, h, title, columns, col_config, query=""):
    """Build a lnsDatatable panel."""
    return {
        "type": "lens",
        "gridData": {"x": x, "y": y, "w": w, "h": h, "i": panel_id},
        "panelIndex": panel_id,
        "title": title,
        "embeddableConfig": {
            "attributes": {
                "title": title,
                "visualizationType": "lnsDatatable",
                "type": "lens",
                "references": panel_ref(),
                "state": {
                    "datasourceStates": {
                        "formBased": {
                            "layers": {
                                "layer1": {
                                    "columns": columns,
                                    "columnOrder": list(columns.keys()),
                                    "incompleteColumns": {},
                                }
                            }
                        }
                    },
                    "visualization": {
                        "layerId": "layer1",
                        "layerType": "data",
                        "columns": col_config,
                        "paging": {"size": 10, "enabled": True},
                    },
                    "query": {"query": query, "language": "kuery"},
                    "filters": [],
                },
            },
            "enhancements": {},
        },
    }


# --- Column helpers ---
def col_date_histogram(label="Timestamp", field="@timestamp", interval="auto"):
    return {
        "label": label,
        "dataType": "date",
        "operationType": "date_histogram",
        "isBucketed": True,
        "scale": "interval",
        "sourceField": field,
        "params": {"interval": interval},
    }


def col_terms(label, field, size=10, order_col="col_metric", order_dir="desc"):
    return {
        "label": label,
        "dataType": "string",
        "operationType": "terms",
        "isBucketed": True,
        "scale": "ordinal",
        "sourceField": field,
        "params": {
            "size": size,
            "orderBy": {"type": "column", "columnId": order_col},
            "orderDirection": order_dir,
        },
    }


def col_count(label="Count"):
    return {
        "label": label,
        "dataType": "number",
        "operationType": "count",
        "isBucketed": False,
        "scale": "ratio",
        "sourceField": "___records___",
    }


def col_average(label, field):
    return {
        "label": label,
        "dataType": "number",
        "operationType": "average",
        "isBucketed": False,
        "scale": "ratio",
        "sourceField": field,
    }


def col_percentile(label, field, pct=95):
    return {
        "label": label,
        "dataType": "number",
        "operationType": "percentile",
        "isBucketed": False,
        "scale": "ratio",
        "sourceField": field,
        "params": {"percentile": pct},
    }


def build_panels():
    """Build all 15 dashboard panels."""
    panels = []

    # ========== ROW 1: KPI Metrics (y=0) ==========
    panels.append(metric_panel(
        "p1", 0, 0, 12, 8, "Total Requetes API",
        "count", "___records___",
        query="service_type.keyword: api",
        subtitle="Dernières 24h",
    ))
    panels.append(metric_panel(
        "p2", 12, 0, 12, 8, "Erreurs (4xx+5xx)",
        "count", "___records___",
        query="http_status >= 400",
        subtitle="Erreurs",
    ))
    panels.append(metric_panel(
        "p3", 24, 0, 12, 8, "Temps Moyen (ms)",
        "average", "duration_ms",
        query="service_type.keyword: api AND duration_ms: *",
        subtitle="Moyenne",
    ))
    panels.append(metric_panel(
        "p4", 36, 0, 12, 8, "P95 (ms)",
        "percentile", "duration_ms",
        query="service_type.keyword: api AND duration_ms: *",
        subtitle="Percentile 95",
        params={"percentile": 95},
    ))

    # ========== ROW 2: Requests over time + HTTP codes (y=8) ==========
    # Bar chart: requests over time
    panels.append(xy_panel(
        "p5", 0, 8, 32, 14, "Requetes API dans le Temps",
        columns={
            "col_x": col_date_histogram(),
            "col_y": col_count("Requetes"),
        },
        series_type="bar",
        query="service_type.keyword: api",
        y_accessors=["col_y"],
        x_accessor="col_x",
        y_title="Requetes",
        x_title="Temps",
    ))

    # Donut: HTTP status code distribution
    panels.append(pie_panel(
        "p6", 32, 8, 16, 14, "Distribution Codes HTTP",
        columns={
            "col_bucket": col_terms("Status Code", "http_status", size=10),
            "col_metric": col_count("Count"),
        },
        shape="donut",
        query="http_status: *",
    ))

    # ========== ROW 3: Response time + category (y=22) ==========
    # Line chart: response time over time
    panels.append(xy_panel(
        "p7", 0, 22, 32, 14, "Temps de Reponse dans le Temps",
        columns={
            "col_x": col_date_histogram(),
            "col_avg": col_average("Moyenne (ms)", "duration_ms"),
            "col_p95": col_percentile("P95 (ms)", "duration_ms", 95),
        },
        series_type="line",
        query="duration_ms: *",
        x_accessor="col_x",
        y_accessors=["col_avg", "col_p95"],
        y_title="ms",
        x_title="Temps",
    ))

    # Pie: response time category
    panels.append(pie_panel(
        "p8", 32, 22, 16, 14, "Categorie Temps de Reponse",
        columns={
            "col_bucket": col_terms("Categorie", "response_category.keyword", size=5),
            "col_metric": col_count("Count"),
        },
        shape="pie",
        query="response_category: *",
    ))

    # ========== ROW 4: Top endpoints table (y=36) ==========
    panels.append(table_panel(
        "p9", 0, 36, 48, 14, "Top 10 Endpoints",
        columns={
            "col_endpoint": col_terms("Endpoint", "request_path.keyword", size=10, order_col="col_count"),
            "col_count": col_count("Requetes"),
            "col_avg": col_average("Temps Moyen (ms)", "duration_ms"),
        },
        col_config=[
            {"columnId": "col_endpoint", "width": 300},
            {"columnId": "col_count", "alignment": "center"},
            {"columnId": "col_avg", "alignment": "center"},
        ],
        query="request_path: *",
    ))

    # ========== ROW 5: By method + by service (y=50) ==========
    # Stacked bar: requests by HTTP method
    panels.append(xy_panel(
        "p10", 0, 50, 24, 14, "Requetes par Methode HTTP",
        columns={
            "col_x": col_date_histogram(),
            "col_split": col_terms("Methode", "http_method.keyword", size=6, order_col="col_y"),
            "col_y": col_count("Count"),
        },
        series_type="bar_stacked",
        query="http_method: *",
        x_accessor="col_x",
        y_accessors=["col_y"],
        split_accessor="col_split",
        y_title="Requetes",
    ))

    # Area stacked: logs by service
    panels.append(xy_panel(
        "p11", 24, 50, 24, 14, "Logs par Service",
        columns={
            "col_x": col_date_histogram(),
            "col_split": col_terms("Service", "service_type.keyword", size=5, order_col="col_y"),
            "col_y": col_count("Count"),
        },
        series_type="area_stacked",
        query="",
        x_accessor="col_x",
        y_accessors=["col_y"],
        split_accessor="col_split",
        y_title="Logs",
    ))

    # ========== ROW 6: By log level (y=64) ==========
    panels.append(xy_panel(
        "p12", 0, 64, 48, 12, "Logs par Niveau",
        columns={
            "col_x": col_date_histogram(),
            "col_split": col_terms("Level", "level.keyword", size=5, order_col="col_y"),
            "col_y": col_count("Count"),
        },
        series_type="bar_stacked",
        query="",
        x_accessor="col_x",
        y_accessors=["col_y"],
        split_accessor="col_split",
        y_title="Logs",
    ))

    # ========== ROW 7: Recent errors + slow requests (y=76) ==========
    panels.append(table_panel(
        "p13", 0, 76, 24, 14, "Erreurs Recentes",
        columns={
            "col_time": col_date_histogram("Timestamp", interval="1h"),
            "col_path": col_terms("Endpoint", "request_path.keyword", size=20, order_col="col_count"),
            "col_count": col_count("Count"),
        },
        col_config=[
            {"columnId": "col_time"},
            {"columnId": "col_path", "width": 250},
            {"columnId": "col_count", "alignment": "center"},
        ],
        query="http_status >= 400",
    ))

    panels.append(table_panel(
        "p14", 24, 76, 24, 14, "Requetes Lentes (>500ms)",
        columns={
            "col_path": col_terms("Endpoint", "request_path.keyword", size=15, order_col="col_avg"),
            "col_avg": col_average("Temps Moyen (ms)", "duration_ms"),
            "col_count": col_count("Count"),
        },
        col_config=[
            {"columnId": "col_path", "width": 250},
            {"columnId": "col_avg", "alignment": "center"},
            {"columnId": "col_count", "alignment": "center"},
        ],
        query="duration_ms > 500",
    ))

    # ========== ROW 8: Correlation ID tracking (y=90) ==========
    panels.append(table_panel(
        "p15", 0, 90, 48, 14, "Suivi par Correlation ID",
        columns={
            "col_corr": col_terms("Correlation ID", "correlation_id.keyword", size=20, order_col="col_count"),
            "col_svc": col_terms("Service", "service_type.keyword", size=5, order_col="col_count"),
            "col_count": col_count("Logs"),
            "col_avg": col_average("Duree (ms)", "duration_ms"),
        },
        col_config=[
            {"columnId": "col_corr", "width": 300},
            {"columnId": "col_svc", "alignment": "center"},
            {"columnId": "col_count", "alignment": "center"},
            {"columnId": "col_avg", "alignment": "center"},
        ],
        query="correlation_id: *",
    ))

    return panels


def build_dashboard_references(panels):
    """Build the dashboard-level references array from panels."""
    refs = []
    for panel in panels:
        pid = panel["panelIndex"]
        refs.append(make_ref(pid, "layer1"))
    return refs


def main():
    panels = build_panels()
    dashboard_refs = build_dashboard_references(panels)

    # Stringify panelsJSON
    panels_json_str = json.dumps(panels, separators=(",", ":"))

    # Build NDJSON lines
    ndjson_lines = []

    # Line 1: Data view (index-pattern)
    ndjson_lines.append(json.dumps({
        "type": "index-pattern",
        "id": DV_ID,
        "attributes": {
            "title": DV_TITLE,
            "timeFieldName": "@timestamp",
            "name": "Recommendation - All Logs",
        },
        "references": [],
        "migrationVersion": {},
    }, separators=(",", ":")))

    # Line 2: Dashboard
    ndjson_lines.append(json.dumps({
        "type": "dashboard",
        "id": DASHBOARD_ID,
        "attributes": {
            "title": "API Logs Dashboard - AR_AS",
            "description": "Dashboard de visualisation des logs API : KPIs, requetes, temps de reponse, erreurs, endpoints, methodes HTTP, services, niveaux de log et correlation",
            "panelsJSON": panels_json_str,
            "optionsJSON": json.dumps({
                "useMargins": True,
                "syncColors": True,
                "syncCursor": True,
                "syncTooltips": False,
                "hidePanelTitles": False,
            }, separators=(",", ":")),
            "timeRestore": True,
            "timeTo": "now",
            "timeFrom": "now-24h",
            "refreshInterval": {"pause": False, "value": 30000},
            "kibanaSavedObjectMeta": {
                "searchSourceJSON": json.dumps({
                    "query": {"query": "", "language": "kuery"},
                    "filter": [],
                }, separators=(",", ":")),
            },
        },
        "references": dashboard_refs,
        "migrationVersion": {},
    }, separators=(",", ":")))

    # Output NDJSON (one JSON object per line)
    for line in ndjson_lines:
        print(line)


if __name__ == "__main__":
    main()
