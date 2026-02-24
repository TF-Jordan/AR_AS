"use client";

import { useEffect, useState, useCallback } from "react";
import { AppShell } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { apiClient } from "@/lib/api";
import type { Tenant, ScoringCriterion } from "@/types/api";
import { Plus, Trash2, RefreshCw, Copy, Eye, EyeOff, Key } from "lucide-react";

interface CriterionInput {
  name: string;
  weight: string;
}

function CreateTenantDialog({ onCreated }: { onCreated: () => void }) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [domain, setDomain] = useState("");
  const [criteria, setCriteria] = useState<CriterionInput[]>([
    { name: "similarity", weight: "0.5" },
    { name: "popularity", weight: "0.5" },
  ]);

  const addCriterion = () => {
    setCriteria([...criteria, { name: "", weight: "0" }]);
  };

  const removeCriterion = (index: number) => {
    setCriteria(criteria.filter((_, i) => i !== index));
  };

  const updateCriterion = (index: number, field: keyof CriterionInput, value: string) => {
    const updated = [...criteria];
    updated[index] = { ...updated[index], [field]: value };
    setCriteria(updated);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const scoringCriteria: ScoringCriterion[] = criteria.map((c) => ({
        name: c.name,
        weight: parseFloat(c.weight),
      }));

      const totalWeight = scoringCriteria.reduce((sum, c) => sum + c.weight, 0);
      if (Math.abs(totalWeight - 1.0) > 0.01) {
        setError(`Les poids doivent totaliser 1.0 (actuellement ${totalWeight.toFixed(2)})`);
        setLoading(false);
        return;
      }

      await apiClient.createTenant({
        name,
        slug,
        domain,
        scoring: { criteria: scoringCriteria },
      });

      setOpen(false);
      setName("");
      setSlug("");
      setDomain("");
      setCriteria([
        { name: "similarity", weight: "0.5" },
        { name: "popularity", weight: "0.5" },
      ]);
      onCreated();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur lors de la cr\u00e9ation");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>
          <Plus className="mr-2 h-4 w-4" />
          Nouveau tenant
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Cr&eacute;er un tenant</DialogTitle>
          <DialogDescription>
            Cr&eacute;ez un nouveau tenant avec ses crit&egrave;res de scoring.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="name">Nom</Label>
            <Input id="name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Mon Entreprise" required />
          </div>
          <div className="space-y-2">
            <Label htmlFor="slug">Slug</Label>
            <Input id="slug" value={slug} onChange={(e) => setSlug(e.target.value.toLowerCase().replace(/[^a-z0-9-_]/g, ""))} placeholder="mon-entreprise" required />
            <p className="text-xs text-muted-foreground">Identifiant unique (lowercase, chiffres, tirets)</p>
          </div>
          <div className="space-y-2">
            <Label htmlFor="domain">Domaine</Label>
            <Input id="domain" value={domain} onChange={(e) => setDomain(e.target.value)} placeholder="e-commerce" required />
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label>Crit&egrave;res de scoring</Label>
              <Button type="button" variant="outline" size="sm" onClick={addCriterion}>
                <Plus className="mr-1 h-3 w-3" />
                Ajouter
              </Button>
            </div>
            {criteria.map((c, i) => (
              <div key={i} className="flex gap-2 items-center">
                <Input
                  placeholder="Nom du crit\u00e8re"
                  value={c.name}
                  onChange={(e) => updateCriterion(i, "name", e.target.value)}
                  className="flex-1"
                  required
                />
                <Input
                  type="number"
                  step="0.01"
                  min="0.01"
                  max="1"
                  placeholder="Poids"
                  value={c.weight}
                  onChange={(e) => updateCriterion(i, "weight", e.target.value)}
                  className="w-24"
                  required
                />
                {criteria.length > 1 && (
                  <Button type="button" variant="ghost" size="icon" onClick={() => removeCriterion(i)}>
                    <Trash2 className="h-4 w-4" />
                  </Button>
                )}
              </div>
            ))}
            <p className="text-xs text-muted-foreground">
              Total: {criteria.reduce((s, c) => s + (parseFloat(c.weight) || 0), 0).toFixed(2)} / 1.00
            </p>
          </div>

          {error && <p className="text-sm text-destructive">{error}</p>}

          <DialogFooter>
            <Button type="submit" disabled={loading}>
              {loading ? "Cr\u00e9ation..." : "Cr\u00e9er"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function TenantApiKeyCell({ apiKey }: { apiKey: string }) {
  const [visible, setVisible] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(apiKey);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="flex items-center gap-1">
      <code className="text-xs bg-muted px-1 py-0.5 rounded">
        {visible ? apiKey : `${apiKey.slice(0, 12)}...`}
      </code>
      <Button variant="ghost" size="icon" className="h-6 w-6" onClick={() => setVisible(!visible)}>
        {visible ? <EyeOff className="h-3 w-3" /> : <Eye className="h-3 w-3" />}
      </Button>
      <Button variant="ghost" size="icon" className="h-6 w-6" onClick={handleCopy}>
        <Copy className="h-3 w-3" />
      </Button>
      {copied && <span className="text-xs text-green-600">Copi&eacute;!</span>}
    </div>
  );
}

export default function TenantsPage() {
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadTenants = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await apiClient.listTenants();
      setTenants(data.tenants);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur de chargement");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadTenants();
  }, [loadTenants]);

  const handleDelete = async (slug: string) => {
    try {
      await apiClient.deleteTenant(slug);
      loadTenants();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur lors de la suppression");
    }
  };

  const handleRegenerateKey = async (slug: string) => {
    try {
      await apiClient.regenerateKey(slug);
      loadTenants();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur lors de la r\u00e9g\u00e9n\u00e9ration");
    }
  };

  const handleToggleStatus = async (tenant: Tenant) => {
    try {
      const newStatus = tenant.status === "active" ? "suspended" : "active";
      await apiClient.updateTenant(tenant.slug, { status: newStatus });
      loadTenants();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur lors de la mise \u00e0 jour");
    }
  };

  return (
    <AppShell>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-3xl font-bold tracking-tight">Gestion des Tenants</h2>
            <p className="text-muted-foreground">
              Cr&eacute;ez et g&eacute;rez les tenants de la plateforme
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={loadTenants}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Rafra&icirc;chir
            </Button>
            <CreateTenantDialog onCreated={loadTenants} />
          </div>
        </div>

        {error && (
          <div className="rounded-lg border border-destructive bg-destructive/10 p-4 text-sm text-destructive">
            {error}
          </div>
        )}

        <Card>
          <CardHeader>
            <CardTitle>Tenants ({tenants.length})</CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="space-y-2">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-12 animate-pulse rounded bg-muted" />
                ))}
              </div>
            ) : tenants.length === 0 ? (
              <p className="text-center py-8 text-muted-foreground">
                Aucun tenant. Cr&eacute;ez-en un pour commencer.
              </p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Nom</TableHead>
                    <TableHead>Slug</TableHead>
                    <TableHead>Domaine</TableHead>
                    <TableHead>Statut</TableHead>
                    <TableHead>Cl&eacute; API</TableHead>
                    <TableHead>Crit&egrave;res</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {tenants.map((tenant) => (
                    <TableRow key={tenant.slug}>
                      <TableCell className="font-medium">{tenant.name}</TableCell>
                      <TableCell>
                        <code className="text-xs bg-muted px-1 py-0.5 rounded">{tenant.slug}</code>
                      </TableCell>
                      <TableCell>{tenant.domain}</TableCell>
                      <TableCell>
                        <Badge
                          variant={tenant.status === "active" ? "default" : "secondary"}
                          className="cursor-pointer"
                          onClick={() => handleToggleStatus(tenant)}
                        >
                          {tenant.status}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <TenantApiKeyCell apiKey={tenant.api_key} />
                      </TableCell>
                      <TableCell>
                        <span className="text-sm text-muted-foreground">
                          {tenant.scoring_config?.criteria?.length || 0} crit&egrave;res
                        </span>
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8"
                            title="R\u00e9g\u00e9n\u00e9rer cl\u00e9 API"
                            onClick={() => handleRegenerateKey(tenant.slug)}
                          >
                            <Key className="h-4 w-4" />
                          </Button>
                          <AlertDialog>
                            <AlertDialogTrigger asChild>
                              <Button variant="ghost" size="icon" className="h-8 w-8 text-destructive">
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            </AlertDialogTrigger>
                            <AlertDialogContent>
                              <AlertDialogHeader>
                                <AlertDialogTitle>Supprimer {tenant.name} ?</AlertDialogTitle>
                                <AlertDialogDescription>
                                  Cette action supprimera le tenant, son sch&eacute;ma PostgreSQL et sa collection Qdrant. Cette action est irr&eacute;versible.
                                </AlertDialogDescription>
                              </AlertDialogHeader>
                              <AlertDialogFooter>
                                <AlertDialogCancel>Annuler</AlertDialogCancel>
                                <AlertDialogAction onClick={() => handleDelete(tenant.slug)}>
                                  Supprimer
                                </AlertDialogAction>
                              </AlertDialogFooter>
                            </AlertDialogContent>
                          </AlertDialog>
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
