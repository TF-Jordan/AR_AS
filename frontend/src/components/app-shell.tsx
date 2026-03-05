"use client";

import { useAuth } from "@/components/auth-provider";
import { LoginForm } from "@/components/login-form";
import { Sidebar } from "@/components/sidebar";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { LogOut, Shield, Building2 } from "lucide-react";

export function AppShell({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, role, platform, logout } = useAuth();

  if (!isAuthenticated) {
    return <LoginForm />;
  }

  return (
    <div className="flex h-screen">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <header className="flex h-16 items-center justify-between border-b px-6">
          <div className="flex items-center gap-2">
            {role === "super_admin" && (
              <Badge variant="default" className="gap-1">
                <Shield className="h-3 w-3" />
                Super Admin
              </Badge>
            )}
            {role === "platform_owner" && (
              <Badge variant="secondary" className="gap-1">
                <Building2 className="h-3 w-3" />
                {platform?.name || "Platform Owner"}
              </Badge>
            )}
          </div>
          <Button variant="ghost" size="sm" onClick={logout}>
            <LogOut className="mr-2 h-4 w-4" />
            Déconnexion
          </Button>
        </header>
        <main className="flex-1 overflow-y-auto p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
