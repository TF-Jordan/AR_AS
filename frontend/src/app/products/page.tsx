"use client";

import { useEffect, useState, useCallback } from "react";
import { AppShell } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
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
import type { Tenant, TenantItem } from "@/types/api";
import { Upload, Trash2, RefreshCw, Package, ChevronLeft, ChevronRight } from "lucide-react";

function ImportDialog({
  tenant,
  onImported,
}: {
  tenant: Tenant;
  onImported: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [jsonInput, setJsonInput] = useState("");
  const [vectorize, setVectorize] = useState(true);
  const [result, setResult] = useState<{ items_imported: number; vectors_indexed: number } | null>(null);

  const handleImport = async () => {
    setError("");
    setResult(null);
    setLoading(true);

    try {
      const items = JSON.parse(jsonInput);
      if (!Array.isArray(items)) {
        throw new Error("Le JSON doit \u00eatre un tableau d'objets");
      }

      const res = await apiClient.importItems(tenant.api_key, items, vectorize);
      setResult(res);
      onImported();
    } catch (e) {
      if (e instanceof SyntaxError) {
        setError("JSON invalide");
      } else {
        setError(e instanceof Error ? e.message : "Erreur d'import");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      setJsonInput(event.target?.result as string);
    };
    reader.readAsText(file);
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm">
          <Upload className="mr-2 h-4 w-4" />
          Importer
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Importer des items</DialogTitle>
          <DialogDescription>
            Importez des items dans le catalogue de {tenant.name}
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label>Fichier JSON</Label>
            <Input type="file" accept=".json" onChange={handleFileUpload} />
          </div>
          <div className="space-y-2">
            <Label>Ou collez le JSON</Label>
            <textarea
              className="flex min-h-[120px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              placeholder={'[\n  {"id": "1", "name": "...", "description": "..."}\n]'}
              value={jsonInput}
              onChange={(e) => setJsonInput(e.target.value)}
            />
          </div>
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="vectorize"
              checked={vectorize}
              onChange={(e) => setVectorize(e.target.checked)}
              className="rounded"
            />
            <Label htmlFor="vectorize">Vectoriser (g&eacute;n&eacute;rer embeddings)</Label>
          </div>

          {error && <p className="text-sm text-destructive">{error}</p>}
          {result && (
            <div className="rounded-lg bg-green-50 border border-green-200 p-3 text-sm">
              Import r&eacute;ussi: {result.items_imported} items, {result.vectors_indexed} vecteurs
            </div>
          )}
        </div>
        <DialogFooter>
          <Button onClick={handleImport} disabled={loading || !jsonInput.trim()}>
            {loading ? "Import en cours..." : "Importer"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function TenantProducts({ tenant }: { tenant: Tenant }) {
  const [items, setItems] = useState<TenantItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [offset, setOffset] = useState(0);
  const limit = 20;

  const loadItems = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await apiClient.listItems(tenant.api_key, limit, offset);
      setItems(data.items);
      setTotal(data.total);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur de chargement");
    } finally {
      setLoading(false);
    }
  }, [tenant.api_key, offset]);

  useEffect(() => {
    loadItems();
  }, [loadItems]);

  const handleDelete = async (itemId: string) => {
    try {
      await apiClient.deleteItem(tenant.api_key, itemId);
      loadItems();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur de suppression");
    }
  };

  const totalPages = Math.ceil(total / limit);
  const currentPage = Math.floor(offset / limit) + 1;

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-lg">{tenant.name}</CardTitle>
            <CardDescription>
              {tenant.slug} &mdash; {total} items
            </CardDescription>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={loadItems}>
              <RefreshCw className="mr-1 h-3 w-3" />
              Rafra&icirc;chir
            </Button>
            <ImportDialog tenant={tenant} onImported={loadItems} />
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {error && (
          <p className="text-sm text-destructive mb-2">{error}</p>
        )}
        {loading ? (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-10 animate-pulse rounded bg-muted" />
            ))}
          </div>
        ) : items.length === 0 ? (
          <p className="text-center py-4 text-muted-foreground">
            Aucun item. Importez des donn&eacute;es pour commencer.
          </p>
        ) : (
          <>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>ID</TableHead>
                  <TableHead>Donn&eacute;es</TableHead>
                  <TableHead>Cr&eacute;&eacute; le</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell>
                      <code className="text-xs bg-muted px-1 py-0.5 rounded">{item.id}</code>
                    </TableCell>
                    <TableCell className="max-w-md">
                      <pre className="text-xs truncate">
                        {JSON.stringify(item.data, null, 0).slice(0, 100)}
                        {JSON.stringify(item.data).length > 100 ? "..." : ""}
                      </pre>
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {new Date(item.created_at).toLocaleDateString("fr-FR")}
                    </TableCell>
                    <TableCell className="text-right">
                      <AlertDialog>
                        <AlertDialogTrigger asChild>
                          <Button variant="ghost" size="icon" className="h-8 w-8 text-destructive">
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </AlertDialogTrigger>
                        <AlertDialogContent>
                          <AlertDialogHeader>
                            <AlertDialogTitle>Supprimer l&apos;item {item.id} ?</AlertDialogTitle>
                            <AlertDialogDescription>
                              L&apos;item sera supprim&eacute; de la base de donn&eacute;es et du vector store.
                            </AlertDialogDescription>
                          </AlertDialogHeader>
                          <AlertDialogFooter>
                            <AlertDialogCancel>Annuler</AlertDialogCancel>
                            <AlertDialogAction onClick={() => handleDelete(item.id)}>
                              Supprimer
                            </AlertDialogAction>
                          </AlertDialogFooter>
                        </AlertDialogContent>
                      </AlertDialog>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>

            {totalPages > 1 && (
              <div className="flex items-center justify-between pt-4">
                <p className="text-sm text-muted-foreground">
                  Page {currentPage} / {totalPages}
                </p>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={offset === 0}
                    onClick={() => setOffset(Math.max(0, offset - limit))}
                  >
                    <ChevronLeft className="h-4 w-4" />
                    Pr&eacute;c&eacute;dent
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={offset + limit >= total}
                    onClick={() => setOffset(offset + limit)}
                  >
                    Suivant
                    <ChevronRight className="ml-1 h-4 w-4" />
                  </Button>
                </div>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}

export default function ProductsPage() {
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
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Gestion des Produits</h2>
          <p className="text-muted-foreground">
            G&eacute;rez les catalogues de produits de chaque tenant
          </p>
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
          <div className="space-y-6">
            {tenants.map((tenant) => (
              <TenantProducts key={tenant.slug} tenant={tenant} />
            ))}
          </div>
        )}
      </div>
    </AppShell>
  );
}
