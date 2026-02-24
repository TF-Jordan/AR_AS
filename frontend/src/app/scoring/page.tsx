"use client";

import { useEffect, useState, useCallback } from "react";
import { AppShell } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Slider } from "@/components/ui/slider";
import { Separator } from "@/components/ui/separator";
import { apiClient } from "@/lib/api";
import type { Tenant, ScoringCriterion } from "@/types/api";
import { Save, Plus, Trash2, RefreshCw } from "lucide-react";

interface EditableCriterion {
  name: string;
  weight: number;
}

function ScoringEditor({
  tenant,
  onSaved,
}: {
  tenant: Tenant;
  onSaved: () => void;
}) {
  const [criteria, setCriteria] = useState<EditableCriterion[]>(
    tenant.scoring_config?.criteria?.map((c) => ({ ...c })) || []
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  const totalWeight = criteria.reduce((sum, c) => sum + c.weight, 0);
  const isValid = Math.abs(totalWeight - 1.0) <= 0.01 && criteria.length > 0;

  const updateWeight = (index: number, weight: number) => {
    const updated = [...criteria];
    updated[index] = { ...updated[index], weight: Math.round(weight * 100) / 100 };
    setCriteria(updated);
  };

  const updateName = (index: number, name: string) => {
    const updated = [...criteria];
    updated[index] = { ...updated[index], name };
    setCriteria(updated);
  };

  const addCriterion = () => {
    setCriteria([...criteria, { name: "", weight: 0 }]);
  };

  const removeCriterion = (index: number) => {
    setCriteria(criteria.filter((_, i) => i !== index));
  };

  const autoBalance = () => {
    if (criteria.length === 0) return;
    const equalWeight = Math.round((1.0 / criteria.length) * 100) / 100;
    const balanced = criteria.map((c, i) => ({
      ...c,
      weight: i === criteria.length - 1
        ? Math.round((1.0 - equalWeight * (criteria.length - 1)) * 100) / 100
        : equalWeight,
    }));
    setCriteria(balanced);
  };

  const handleSave = async () => {
    setError("");
    setSuccess(false);
    setSaving(true);

    try {
      const scoringCriteria: ScoringCriterion[] = criteria.map((c) => ({
        name: c.name,
        weight: c.weight,
      }));

      await apiClient.updateTenant(tenant.slug, {
        scoring: { criteria: scoringCriteria },
      });

      setSuccess(true);
      onSaved();
      setTimeout(() => setSuccess(false), 3000);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur lors de la sauvegarde");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>{tenant.name}</CardTitle>
            <CardDescription>
              {tenant.slug} &mdash; {tenant.domain}
            </CardDescription>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={autoBalance}>
              &Eacute;quilibrer
            </Button>
            <Button size="sm" onClick={handleSave} disabled={saving || !isValid}>
              <Save className="mr-2 h-4 w-4" />
              {saving ? "Sauvegarde..." : "Sauvegarder"}
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {criteria.map((criterion, index) => (
          <div key={index} className="space-y-2">
            <div className="flex items-center gap-2">
              <Input
                value={criterion.name}
                onChange={(e) => updateName(index, e.target.value)}
                placeholder="Nom du crit\u00e8re"
                className="w-48"
              />
              <div className="flex-1">
                <Slider
                  value={[criterion.weight * 100]}
                  onValueChange={([val]) => updateWeight(index, val / 100)}
                  max={100}
                  step={1}
                />
              </div>
              <span className="w-16 text-right text-sm font-mono">
                {(criterion.weight * 100).toFixed(0)}%
              </span>
              {criteria.length > 1 && (
                <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => removeCriterion(index)}>
                  <Trash2 className="h-4 w-4" />
                </Button>
              )}
            </div>
          </div>
        ))}

        <div className="flex items-center justify-between pt-2">
          <Button variant="outline" size="sm" onClick={addCriterion}>
            <Plus className="mr-1 h-3 w-3" />
            Ajouter un crit&egrave;re
          </Button>
          <span className={`text-sm font-medium ${isValid ? "text-green-600" : "text-destructive"}`}>
            Total: {(totalWeight * 100).toFixed(0)}% {isValid ? "\u2713" : "(doit \u00eatre 100%)"}
          </span>
        </div>

        {error && <p className="text-sm text-destructive">{error}</p>}
        {success && <p className="text-sm text-green-600">Configuration sauvegard&eacute;e avec succ&egrave;s!</p>}
      </CardContent>
    </Card>
  );
}

export default function ScoringPage() {
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

  return (
    <AppShell>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-3xl font-bold tracking-tight">Configuration Scoring</h2>
            <p className="text-muted-foreground">
              Configurez les crit&egrave;res de scoring pour chaque tenant
            </p>
          </div>
          <Button variant="outline" onClick={loadTenants}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Rafra&icirc;chir
          </Button>
        </div>

        {error && (
          <div className="rounded-lg border border-destructive bg-destructive/10 p-4 text-sm text-destructive">
            {error}
          </div>
        )}

        {loading ? (
          <div className="space-y-4">
            {[1, 2].map((i) => (
              <Card key={i}>
                <CardContent className="p-6">
                  <div className="h-32 animate-pulse rounded bg-muted" />
                </CardContent>
              </Card>
            ))}
          </div>
        ) : tenants.length === 0 ? (
          <Card>
            <CardContent className="py-8 text-center text-muted-foreground">
              Aucun tenant. Cr&eacute;ez d&apos;abord un tenant depuis la page Tenants.
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-4">
            {tenants.map((tenant) => (
              <ScoringEditor key={tenant.slug} tenant={tenant} onSaved={loadTenants} />
            ))}
          </div>
        )}
      </div>
    </AppShell>
  );
}
