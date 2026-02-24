"use client";

import { useEffect, useState, useCallback } from "react";
import { AppShell } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { apiClient } from "@/lib/api";
import type { PlatformMetrics, SystemStatus } from "@/types/api";
import {
  RefreshCw,
  CheckCircle,
  XCircle,
  Server,
  Database,
  HardDrive,
  Activity,
} from "lucide-react";

function ServiceCard({
  name,
  icon: Icon,
  healthy,
  description,
}: {
  name: string;
  icon: React.ElementType;
  healthy: boolean;
  description: string;
}) {
  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-start gap-4">
          <div className={`rounded-lg p-2 ${healthy ? "bg-green-100" : "bg-red-100"}`}>
            <Icon className={`h-6 w-6 ${healthy ? "text-green-600" : "text-red-600"}`} />
          </div>
          <div className="flex-1">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold">{name}</h3>
              <Badge variant={healthy ? "default" : "destructive"}>
                {healthy ? "Actif" : "Inactif"}
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground mt-1">{description}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function MetricBar({
  label,
  value,
  maxValue,
  unit,
}: {
  label: string;
  value: number;
  maxValue: number;
  unit: string;
}) {
  const percentage = maxValue > 0 ? Math.min((value / maxValue) * 100, 100) : 0;
  const color = percentage > 80 ? "bg-red-500" : percentage > 60 ? "bg-yellow-500" : "bg-green-500";

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-sm">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-medium">
          {value.toLocaleString()} {unit}
        </span>
      </div>
      <div className="h-2 w-full rounded-full bg-secondary">
        <div
          className={`h-full rounded-full transition-all ${color}`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}

export default function MonitoringPage() {
  const [metrics, setMetrics] = useState<PlatformMetrics | null>(null);
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [autoRefresh, setAutoRefresh] = useState(false);

  const loadData = useCallback(async () => {
    setError("");
    try {
      const [metricsData, statusData] = await Promise.all([
        apiClient.getMetrics(),
        apiClient.getStatus(),
      ]);
      setMetrics(metricsData);
      setStatus(statusData);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur de chargement");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(loadData, 10000);
    return () => clearInterval(interval);
  }, [autoRefresh, loadData]);

  const servicesHealthy = metrics
    ? Object.values(metrics.services).filter(Boolean).length
    : 0;
  const servicesTotal = metrics
    ? Object.values(metrics.services).length
    : 0;

  return (
    <AppShell>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-3xl font-bold tracking-tight">Monitoring</h2>
            <p className="text-muted-foreground">
              Surveillance en temps r&eacute;el de la plateforme
            </p>
          </div>
          <div className="flex gap-2">
            <Button
              variant={autoRefresh ? "default" : "outline"}
              size="sm"
              onClick={() => setAutoRefresh(!autoRefresh)}
            >
              <Activity className="mr-2 h-4 w-4" />
              {autoRefresh ? "Auto-refresh ON (10s)" : "Auto-refresh OFF"}
            </Button>
            <Button variant="outline" size="sm" onClick={loadData}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Rafra&icirc;chir
            </Button>
          </div>
        </div>

        {error && (
          <div className="rounded-lg border border-destructive bg-destructive/10 p-4 text-sm text-destructive">
            {error}
          </div>
        )}

        {loading ? (
          <div className="grid gap-4 md:grid-cols-3">
            {[1, 2, 3].map((i) => (
              <Card key={i}>
                <CardContent className="p-6">
                  <div className="h-20 animate-pulse rounded bg-muted" />
                </CardContent>
              </Card>
            ))}
          </div>
        ) : metrics ? (
          <>
            {/* Platform Status */}
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>Statut de la plateforme</CardTitle>
                  <Badge
                    variant={status?.status === "operational" ? "default" : "destructive"}
                    className="text-sm"
                  >
                    {status?.status === "operational" ? "Op\u00e9rationnel" : "D\u00e9grad\u00e9"}
                  </Badge>
                </div>
                <CardDescription>
                  {servicesHealthy}/{servicesTotal} services actifs
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid gap-4 md:grid-cols-3">
                  <ServiceCard
                    name="PostgreSQL"
                    icon={Database}
                    healthy={metrics.services.postgresql}
                    description="Base de donn&eacute;es relationnelle"
                  />
                  <ServiceCard
                    name="Qdrant"
                    icon={HardDrive}
                    healthy={metrics.services.qdrant}
                    description="Base de donn&eacute;es vectorielle"
                  />
                  <ServiceCard
                    name="Redis"
                    icon={Server}
                    healthy={metrics.services.redis}
                    description="Cache et file d&apos;attente"
                  />
                </div>
              </CardContent>
            </Card>

            {/* Platform Metrics */}
            <div className="grid gap-4 md:grid-cols-2">
              <Card>
                <CardHeader>
                  <CardTitle>M&eacute;triques globales</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <MetricBar
                    label="Tenants actifs"
                    value={metrics.active_tenants}
                    maxValue={Math.max(metrics.total_tenants, 1)}
                    unit={`/ ${metrics.total_tenants}`}
                  />
                  <MetricBar
                    label="Items total"
                    value={metrics.total_items}
                    maxValue={Math.max(metrics.total_items, 1)}
                    unit="items"
                  />
                  <MetricBar
                    label="Vecteurs index\u00e9s"
                    value={metrics.total_vectors}
                    maxValue={Math.max(metrics.total_items, 1)}
                    unit="vecteurs"
                  />
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>R&eacute;partition par tenant</CardTitle>
                </CardHeader>
                <CardContent>
                  {metrics.tenant_stats.length === 0 ? (
                    <p className="text-center py-4 text-muted-foreground">
                      Aucun tenant actif
                    </p>
                  ) : (
                    <div className="space-y-3">
                      {metrics.tenant_stats.map((ts) => {
                        const itemShare = metrics.total_items > 0
                          ? (ts.items_count / metrics.total_items * 100).toFixed(1)
                          : "0";
                        return (
                          <div key={ts.slug} className="flex items-center gap-3">
                            <div className="flex-1">
                              <div className="flex items-center justify-between mb-1">
                                <span className="text-sm font-medium">{ts.slug}</span>
                                <span className="text-xs text-muted-foreground">
                                  {itemShare}% des items
                                </span>
                              </div>
                              <div className="flex gap-4 text-xs text-muted-foreground">
                                <span>{ts.items_count} items</span>
                                <span>{ts.vectors_count} vecteurs</span>
                              </div>
                            </div>
                            {ts.error ? (
                              <XCircle className="h-4 w-4 text-destructive" />
                            ) : (
                              <CheckCircle className="h-4 w-4 text-green-500" />
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          </>
        ) : null}
      </div>
    </AppShell>
  );
}
