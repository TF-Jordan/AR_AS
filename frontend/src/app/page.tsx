"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/app-shell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { apiClient } from "@/lib/api";
import type { PlatformMetrics, SystemStatus } from "@/types/api";
import { Users, Package, Database, Activity, CheckCircle, XCircle } from "lucide-react";

function ServiceBadge({ name, healthy }: { name: string; healthy: boolean }) {
  return (
    <div className="flex items-center gap-2">
      {healthy ? (
        <CheckCircle className="h-4 w-4 text-green-500" />
      ) : (
        <XCircle className="h-4 w-4 text-destructive" />
      )}
      <span className="text-sm font-medium">{name}</span>
      <Badge variant={healthy ? "default" : "destructive"}>
        {healthy ? "OK" : "Down"}
      </Badge>
    </div>
  );
}

function KpiCard({
  title,
  value,
  icon: Icon,
  description,
}: {
  title: string;
  value: string | number;
  icon: React.ElementType;
  description?: string;
}) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        {description && (
          <p className="text-xs text-muted-foreground">{description}</p>
        )}
      </CardContent>
    </Card>
  );
}

export default function DashboardPage() {
  const [metrics, setMetrics] = useState<PlatformMetrics | null>(null);
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    setLoading(true);
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
  }

  return (
    <AppShell>
      <div className="space-y-6">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Dashboard</h2>
          <p className="text-muted-foreground">
            Vue d&apos;ensemble de la plateforme RaaS
          </p>
        </div>

        {error && (
          <div className="rounded-lg border border-destructive bg-destructive/10 p-4 text-sm text-destructive">
            {error}
          </div>
        )}

        {loading ? (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            {[1, 2, 3, 4].map((i) => (
              <Card key={i}>
                <CardContent className="p-6">
                  <div className="h-16 animate-pulse rounded bg-muted" />
                </CardContent>
              </Card>
            ))}
          </div>
        ) : metrics ? (
          <>
            {/* KPI Cards */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              <KpiCard
                title="Tenants actifs"
                value={metrics.active_tenants}
                icon={Users}
                description={`${metrics.total_tenants} total`}
              />
              <KpiCard
                title="Total items"
                value={metrics.total_items.toLocaleString()}
                icon={Package}
                description="Tous tenants confondus"
              />
              <KpiCard
                title="Total vecteurs"
                value={metrics.total_vectors.toLocaleString()}
                icon={Database}
                description="Index\u00e9s dans Qdrant"
              />
              <KpiCard
                title="Statut syst\u00e8me"
                value={status?.status === "operational" ? "Op\u00e9rationnel" : "D\u00e9grad\u00e9"}
                icon={Activity}
                description={status?.status === "operational" ? "Tous services OK" : "V\u00e9rifier les services"}
              />
            </div>

            {/* Services Health */}
            <Card>
              <CardHeader>
                <CardTitle>Sant&eacute; des services</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid gap-4 md:grid-cols-3">
                  <ServiceBadge name="PostgreSQL" healthy={metrics.services.postgresql} />
                  <ServiceBadge name="Qdrant" healthy={metrics.services.qdrant} />
                  <ServiceBadge name="Redis" healthy={metrics.services.redis} />
                </div>
              </CardContent>
            </Card>

            {/* Per-Tenant Stats */}
            {metrics.tenant_stats.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle>Statistiques par tenant</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {metrics.tenant_stats.map((ts) => (
                      <div
                        key={ts.slug}
                        className="flex items-center justify-between rounded-lg border p-3"
                      >
                        <div className="font-medium">{ts.slug}</div>
                        <div className="flex gap-4 text-sm text-muted-foreground">
                          <span>{ts.items_count} items</span>
                          <span>{ts.vectors_count} vecteurs</span>
                          {ts.error && (
                            <Badge variant="destructive">Erreur</Badge>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </>
        ) : null}
      </div>
    </AppShell>
  );
}
