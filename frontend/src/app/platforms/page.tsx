"use client";

import { useEffect, useState, useCallback } from "react";
import { AppShell } from "@/components/app-shell";
import { useAuth } from "@/components/auth-provider";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { apiClient } from "@/lib/api";
import type { PlatformEntry } from "@/types/api";
import {
  RefreshCw,
  Eye,
  Power,
  Building2,
  Users,
  ChevronDown,
  ChevronRight,
} from "lucide-react";

function PlatformDetailDialog({ platform }: { platform: PlatformEntry }) {
  const [detail, setDetail] = useState<PlatformEntry | null>(null);
  const [loading, setLoading] = useState(false);

  const loadDetail = async () => {
    setLoading(true);
    try {
      const data = await apiClient.getPlatformDetail(platform.slug);
      setDetail(data);
    } catch {
      // silently fail
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="ghost" size="icon" className="h-8 w-8" onClick={loadDetail}>
          <Eye className="h-4 w-4" />
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-lg max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{platform.name}</DialogTitle>
        </DialogHeader>
        {loading ? (
          <div className="h-20 animate-pulse rounded bg-muted" />
        ) : detail ? (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div className="text-muted-foreground">Slug</div>
              <code className="bg-muted px-1 rounded">{detail.slug}</code>
              <div className="text-muted-foreground">Email</div>
              <div>{detail.email}</div>
              <div className="text-muted-foreground">Domaine</div>
              <div>{detail.domain}</div>
              <div className="text-muted-foreground">Statut</div>
              <Badge variant={detail.is_active ? "default" : "secondary"}>
                {detail.is_active ? "Actif" : "Désactivé"}
              </Badge>
              <div className="text-muted-foreground">API Key</div>
              <code className="bg-muted px-1 rounded text-xs break-all">{detail.api_key}</code>
              <div className="text-muted-foreground">Créé le</div>
              <div>{new Date(detail.created_at).toLocaleDateString("fr-FR")}</div>
            </div>

            {detail.tenants && detail.tenants.length > 0 && (
              <div>
                <h4 className="font-semibold mb-2">Tenants ({detail.tenants.length})</h4>
                <div className="space-y-2">
                  {detail.tenants.map((t) => (
                    <div key={t.slug} className="flex items-center justify-between border rounded p-2 text-sm">
                      <div>
                        <span className="font-medium">{t.name}</span>
                        <span className="text-muted-foreground ml-2">({t.slug})</span>
                      </div>
                      <Badge variant={t.status === "active" ? "default" : "secondary"}>
                        {t.status}
                      </Badge>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}

export default function PlatformsPage() {
  const { role } = useAuth();
  const [platforms, setPlatforms] = useState<PlatformEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadPlatforms = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await apiClient.listPlatforms();
      setPlatforms(data.platforms);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur de chargement");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadPlatforms();
  }, [loadPlatforms]);

  const handleToggleActive = async (platform: PlatformEntry) => {
    try {
      await apiClient.updatePlatform(platform.slug, { is_active: !platform.is_active });
      loadPlatforms();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur lors de la mise à jour");
    }
  };

  if (role !== "super_admin") {
    return (
      <AppShell>
        <div className="flex items-center justify-center h-full">
          <p className="text-muted-foreground">Accès réservé au super administrateur.</p>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-3xl font-bold tracking-tight">Gestion des Plateformes</h2>
            <p className="text-muted-foreground">
              Supervisez toutes les plateformes inscrites
            </p>
          </div>
          <Button variant="outline" onClick={loadPlatforms}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Rafraîchir
          </Button>
        </div>

        {error && (
          <div className="rounded-lg border border-destructive bg-destructive/10 p-4 text-sm text-destructive">
            {error}
          </div>
        )}

        <Card>
          <CardHeader>
            <CardTitle>Plateformes ({platforms.length})</CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="space-y-2">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-12 animate-pulse rounded bg-muted" />
                ))}
              </div>
            ) : platforms.length === 0 ? (
              <p className="text-center py-8 text-muted-foreground">
                Aucune plateforme inscrite.
              </p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Nom</TableHead>
                    <TableHead>Slug</TableHead>
                    <TableHead>Email</TableHead>
                    <TableHead>Domaine</TableHead>
                    <TableHead>Tenants</TableHead>
                    <TableHead>Statut</TableHead>
                    <TableHead>Créé le</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {platforms.map((p) => (
                    <TableRow key={p.slug}>
                      <TableCell className="font-medium">{p.name}</TableCell>
                      <TableCell>
                        <code className="text-xs bg-muted px-1 py-0.5 rounded">{p.slug}</code>
                      </TableCell>
                      <TableCell className="text-sm">{p.email}</TableCell>
                      <TableCell>{p.domain}</TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1">
                          <Users className="h-3 w-3" />
                          <span>{p.tenants_count}</span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant={p.is_active ? "default" : "secondary"}>
                          {p.is_active ? "Actif" : "Désactivé"}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {new Date(p.created_at).toLocaleDateString("fr-FR")}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-1">
                          <PlatformDetailDialog platform={p} />
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8"
                            title={p.is_active ? "Désactiver" : "Activer"}
                            onClick={() => handleToggleActive(p)}
                          >
                            <Power className={`h-4 w-4 ${p.is_active ? "text-green-500" : "text-destructive"}`} />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>
    </AppShell>
  );
}
