"use client";

import { useState } from "react";
import { useAuth } from "@/components/auth-provider";
import { apiClient } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

type Tab = "admin" | "platform" | "register";

export function LoginForm() {
  const { login } = useAuth();
  const [tab, setTab] = useState<Tab>("platform");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // Admin fields
  const [adminKey, setAdminKey] = useState("");

  // Platform login fields
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  // Register fields
  const [regName, setRegName] = useState("");
  const [regSlug, setRegSlug] = useState("");
  const [regDomain, setRegDomain] = useState("");
  const [regEmail, setRegEmail] = useState("");
  const [regPassword, setRegPassword] = useState("");
  const [regPasswordConfirm, setRegPasswordConfirm] = useState("");

  const handleAdminLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const res = await apiClient.loginAdmin(adminKey);
      login(res.token, res.role, res.platform || undefined);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Clé invalide");
    } finally {
      setLoading(false);
    }
  };

  const handlePlatformLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const res = await apiClient.loginPlatform(email, password);
      login(res.token, res.role, res.platform || undefined);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Email ou mot de passe incorrect");
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (regPassword !== regPasswordConfirm) {
      setError("Les mots de passe ne correspondent pas");
      return;
    }

    if (regPassword.length < 6) {
      setError("Le mot de passe doit faire au moins 6 caractères");
      return;
    }

    setLoading(true);

    try {
      const res = await apiClient.registerPlatform({
        name: regName,
        slug: regSlug,
        domain: regDomain,
        email: regEmail,
        password: regPassword,
      });
      login(res.token, res.role, res.platform || undefined);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur lors de l'inscription");
    } finally {
      setLoading(false);
    }
  };

  const tabClass = (t: Tab) =>
    `flex-1 py-2 text-center text-sm font-medium transition-colors border-b-2 cursor-pointer ${
      tab === t
        ? "border-primary text-primary"
        : "border-transparent text-muted-foreground hover:text-foreground"
    }`;

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/50">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">AR_AS Platform</CardTitle>
          <CardDescription>
            Connectez-vous pour accéder au tableau de bord
          </CardDescription>
        </CardHeader>
        <CardContent>
          {/* Tabs */}
          <div className="flex border-b mb-6">
            <button className={tabClass("platform")} onClick={() => { setTab("platform"); setError(""); }}>
              Plateforme
            </button>
            <button className={tabClass("admin")} onClick={() => { setTab("admin"); setError(""); }}>
              Super Admin
            </button>
            <button className={tabClass("register")} onClick={() => { setTab("register"); setError(""); }}>
              Inscription
            </button>
          </div>

          {/* Admin Login */}
          {tab === "admin" && (
            <form onSubmit={handleAdminLogin} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="admin-key">Clé Super Admin</Label>
                <Input
                  id="admin-key"
                  type="password"
                  placeholder="admin_secret_..."
                  value={adminKey}
                  onChange={(e) => setAdminKey(e.target.value)}
                  required
                />
              </div>
              {error && <p className="text-sm text-destructive">{error}</p>}
              <Button type="submit" className="w-full" disabled={loading}>
                {loading ? "Connexion..." : "Se connecter"}
              </Button>
            </form>
          )}

          {/* Platform Login */}
          {tab === "platform" && (
            <form onSubmit={handlePlatformLogin} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="admin@monsite.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="password">Mot de passe</Label>
                <Input
                  id="password"
                  type="password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              </div>
              {error && <p className="text-sm text-destructive">{error}</p>}
              <Button type="submit" className="w-full" disabled={loading}>
                {loading ? "Connexion..." : "Se connecter"}
              </Button>
            </form>
          )}

          {/* Registration */}
          {tab === "register" && (
            <form onSubmit={handleRegister} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="reg-name">Nom de la plateforme</Label>
                <Input
                  id="reg-name"
                  placeholder="Mon Entreprise"
                  value={regName}
                  onChange={(e) => setRegName(e.target.value)}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="reg-slug">Slug</Label>
                <Input
                  id="reg-slug"
                  placeholder="mon-entreprise"
                  value={regSlug}
                  onChange={(e) => setRegSlug(e.target.value.toLowerCase().replace(/[^a-z0-9-_]/g, ""))}
                  required
                />
                <p className="text-xs text-muted-foreground">Identifiant unique (minuscules, chiffres, tirets)</p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="reg-domain">Domaine</Label>
                <Input
                  id="reg-domain"
                  placeholder="e-commerce"
                  value={regDomain}
                  onChange={(e) => setRegDomain(e.target.value)}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="reg-email">Email</Label>
                <Input
                  id="reg-email"
                  type="email"
                  placeholder="admin@monsite.com"
                  value={regEmail}
                  onChange={(e) => setRegEmail(e.target.value)}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="reg-password">Mot de passe</Label>
                <Input
                  id="reg-password"
                  type="password"
                  placeholder="Min. 6 caractères"
                  value={regPassword}
                  onChange={(e) => setRegPassword(e.target.value)}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="reg-password-confirm">Confirmer le mot de passe</Label>
                <Input
                  id="reg-password-confirm"
                  type="password"
                  placeholder="••••••••"
                  value={regPasswordConfirm}
                  onChange={(e) => setRegPasswordConfirm(e.target.value)}
                  required
                />
              </div>
              {error && <p className="text-sm text-destructive">{error}</p>}
              <Button type="submit" className="w-full" disabled={loading}>
                {loading ? "Inscription..." : "Créer mon compte"}
              </Button>
            </form>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
