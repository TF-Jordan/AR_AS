"use client";

import { useState } from "react";
import { useAuth } from "@/components/auth-provider";
import { apiClient } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export function LoginForm() {
  const { login } = useAuth();
  const [key, setKey] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      // Test the key by fetching tenant list
      apiClient.setAdminKey(key);
      await apiClient.listTenants();
      login(key);
    } catch {
      setError("Cl\u00e9 API invalide ou serveur inaccessible");
      apiClient.setAdminKey("");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/50">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">AR_AS Admin</CardTitle>
          <CardDescription>
            Entrez votre cl&eacute; API admin pour acc&eacute;der au tableau de bord
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="api-key">Cl&eacute; API Admin</Label>
              <Input
                id="api-key"
                type="password"
                placeholder="admin_secret_..."
                value={key}
                onChange={(e) => setKey(e.target.value)}
                required
              />
            </div>
            {error && (
              <p className="text-sm text-destructive">{error}</p>
            )}
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? "Connexion..." : "Se connecter"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
