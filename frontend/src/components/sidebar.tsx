"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Users,
  SlidersHorizontal,
  Package,
  Activity,
  Shield,
  Building2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/components/auth-provider";

const superAdminNav = [
  { name: "Dashboard", href: "/", icon: LayoutDashboard },
  { name: "Plateformes", href: "/platforms", icon: Building2 },
  { name: "Monitoring", href: "/monitoring", icon: Activity },
];

const platformOwnerNav = [
  { name: "Dashboard", href: "/", icon: LayoutDashboard },
  { name: "Tenants", href: "/tenants", icon: Users },
  { name: "Scoring", href: "/scoring", icon: SlidersHorizontal },
  { name: "Produits", href: "/products", icon: Package },
  { name: "Monitoring", href: "/monitoring", icon: Activity },
];

export function Sidebar() {
  const pathname = usePathname();
  const { role, platform } = useAuth();

  const navigation = role === "super_admin" ? superAdminNav : platformOwnerNav;
  const title = role === "super_admin" ? "Super Admin" : platform?.name || "AR_AS";

  return (
    <div className="flex h-full w-64 flex-col bg-card border-r">
      <div className="flex h-16 items-center px-6 border-b">
        <div className="flex items-center gap-2">
          {role === "super_admin" && <Shield className="h-5 w-5 text-primary" />}
          {role === "platform_owner" && <Building2 className="h-5 w-5 text-primary" />}
          <h1 className="text-xl font-bold truncate">{title}</h1>
        </div>
      </div>
      <nav className="flex-1 space-y-1 px-3 py-4">
        {navigation.map((item) => {
          const isActive = pathname === item.href ||
            (item.href !== "/" && pathname.startsWith(item.href));
          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
              )}
            >
              <item.icon className="h-5 w-5" />
              {item.name}
            </Link>
          );
        })}
      </nav>
      <div className="border-t p-4">
        <p className="text-xs text-muted-foreground">
          {role === "super_admin" ? "Super Admin" : platform?.email || ""}
        </p>
        <p className="text-xs text-muted-foreground mt-1">
          AR_AS RaaS Platform v2.0
        </p>
      </div>
    </div>
  );
}
