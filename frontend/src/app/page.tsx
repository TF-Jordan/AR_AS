"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/app-shell";
import { useAuth } from "@/components/auth-provider";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { apiClient } from "@/lib/api";
import type { SuperAdminDashboard, PlatformDashboard } from "@/types/api";
import {
  Users,
  Package,
  Database,
  Activity,
  Building2,
  CheckCircle,
  XCircle,
  Shield,
} from "lucide-react";

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

function SuperAdminDashboardView() {
  const [data, setData] = useState<SuperAdminDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    setLoading(true);
    setError("");
    try {
      const dashboard = await apiClient.getSuperAdminDashboard();
      setData(dashboard);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur de chargement");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Dashboard Super Admin</h2>
        <p className="text-muted-foreground">
          Vue d&apos;ensemble globale de la plateforme RaaS
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
      ) : data ? (
        <>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <KpiCard
              title="Plateformes"
              value={data.active_platforms}
              icon={Building2}
              description={`${data.total_platforms} total`}
            />
            <KpiCard
              title="Tenants actifs"
              value={data.active_tenants}
              icon={Users}
              description={`${data.total_tenants} total`}
            />
            <KpiCard
              title="Event Bus"
              value={data.event_bus.handlers}
              icon={Activity}
              description={`${data.event_bus.pending_tasks} tâches en cours`}
            />
            <KpiCard
              title="Services"
              value={`${Object.values(data.services).filter(Boolean).length}/${Object.keys(data.services).length}`}
              icon={Shield}
              description="Services actifs"
            />
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Santé des services</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-3">
                {Object.entries(data.services).map(([name, healthy]) => (
                  <ServiceBadge key={name} name={name} healthy={healthy} />
                ))}
              </div>
            </CardContent>
          </Card>
        </>
      ) : null}
    </div>
  );
}

function PlatformOwnerDashboardView() {
  const [data, setData] = useState<PlatformDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    setLoading(true);
    setError("");
    try {
      const dashboard = await apiClient.getPlatformDashboard();
      setData(dashboard);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur de chargement");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Dashboard</h2>
        <p className="text-muted-foreground">
          Vue d&apos;ensemble de votre plateforme
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
      ) : data ? (
        <>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <KpiCard
              title="Tenants actifs"
              value={data.active_tenants}
              icon={Users}
              description={`${data.total_tenants} total`}
            />
            <KpiCard
              title="Total items"
              value={data.total_items.toLocaleString()}
              icon={Package}
              description="Tous tenants confondus"
            />
            <KpiCard
              title="Total vecteurs"
              value={data.total_vectors.toLocaleString()}
              icon={Database}
              description="Indexés dans Qdrant"
            />
            <KpiCard
              title="Plateforme"
              value={data.platform_name}
              icon={Building2}
              description={data.platform_slug}
            />
          </div>

          {data.tenant_stats.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Statistiques par tenant</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {data.tenant_stats.map((ts) => (
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
  );
}

export default function DashboardPage() {
  const { role } = useAuth();

  return (
    <AppShell>
      {role === "super_admin" ? (
        <SuperAdminDashboardView />
      ) : (
        <PlatformOwnerDashboardView />
      )}
    </AppShell>
  );
}
