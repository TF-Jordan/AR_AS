import type {
  Tenant,
  TenantListResponse,
  TenantStats,
  PlatformMetrics,
  SystemStatus,
  ItemsListResponse,
  CreateTenantRequest,
  UpdateTenantRequest,
  AuthResponse,
  PlatformEntry,
  PlatformListResponse,
  SuperAdminDashboard,
  PlatformDashboard,
} from "@/types/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

class ApiClient {
  private token: string;
  private adminKey: string;

  constructor() {
    this.token = "";
    this.adminKey = "";
  }

  setToken(token: string) {
    this.token = token;
  }

  getToken(): string {
    return this.token;
  }

  setAdminKey(key: string) {
    this.adminKey = key;
  }

  getAdminKey(): string {
    return this.adminKey;
  }

  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...(options.headers as Record<string, string> || {}),
    };

    if (this.token) {
      headers["Authorization"] = `Bearer ${this.token}`;
    }

    if (this.adminKey) {
      headers["X-API-Key"] = this.adminKey;
    }

    const response = await fetch(`${API_URL}${path}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || `API error: ${response.status}`);
    }

    if (response.status === 204) {
      return undefined as T;
    }

    return response.json();
  }

  // ── Auth ──

  async loginAdmin(key: string): Promise<AuthResponse> {
    return this.request<AuthResponse>("/auth/login/admin", {
      method: "POST",
      body: JSON.stringify({ key }),
    });
  }

  async loginPlatform(email: string, password: string): Promise<AuthResponse> {
    return this.request<AuthResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
  }

  async registerPlatform(data: {
    name: string;
    slug: string;
    domain: string;
    email: string;
    password: string;
  }): Promise<AuthResponse> {
    return this.request<AuthResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  // ── Super Admin ──

  async getSuperAdminDashboard(): Promise<SuperAdminDashboard> {
    return this.request<SuperAdminDashboard>("/super-admin/dashboard");
  }

  async getSuperAdminStatus(): Promise<SystemStatus> {
    return this.request<SystemStatus>("/super-admin/status");
  }

  async listPlatforms(): Promise<PlatformListResponse> {
    return this.request<PlatformListResponse>("/super-admin/platforms");
  }

  async getPlatformDetail(slug: string): Promise<PlatformEntry> {
    return this.request<PlatformEntry>(`/super-admin/platforms/${slug}`);
  }

  async updatePlatform(slug: string, data: { is_active?: boolean; name?: string }): Promise<PlatformEntry> {
    return this.request<PlatformEntry>(`/super-admin/platforms/${slug}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  }

  async toggleTenantStatus(platformSlug: string, tenantSlug: string): Promise<{ tenant: string; status: string }> {
    return this.request(`/super-admin/platforms/${platformSlug}/tenants/${tenantSlug}/toggle`, {
      method: "PUT",
    });
  }

  // ── Platform Owner ──

  async getPlatformDashboard(): Promise<PlatformDashboard> {
    return this.request<PlatformDashboard>("/platform/dashboard");
  }

  async listMyTenants(): Promise<TenantListResponse> {
    return this.request<TenantListResponse>("/platform/tenants");
  }

  async getMyTenant(slug: string): Promise<Tenant> {
    return this.request<Tenant>(`/platform/tenants/${slug}`);
  }

  async createMyTenant(data: CreateTenantRequest): Promise<Tenant> {
    return this.request<Tenant>("/platform/tenants", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async updateMyTenant(slug: string, data: UpdateTenantRequest): Promise<Tenant> {
    return this.request<Tenant>(`/platform/tenants/${slug}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  }

  async deleteMyTenant(slug: string): Promise<void> {
    return this.request<void>(`/platform/tenants/${slug}`, {
      method: "DELETE",
    });
  }

  async regenerateMyTenantKey(slug: string): Promise<Tenant> {
    return this.request<Tenant>(`/platform/tenants/${slug}/regenerate-key`, {
      method: "POST",
    });
  }

  async getMyTenantStats(slug: string): Promise<TenantStats> {
    return this.request<TenantStats>(`/platform/tenants/${slug}/stats`);
  }

  async listMyTenantItems(slug: string, limit = 100, offset = 0): Promise<ItemsListResponse> {
    return this.request<ItemsListResponse>(`/platform/tenants/${slug}/items?limit=${limit}&offset=${offset}`);
  }

  async importMyTenantItems(
    slug: string,
    items: Record<string, unknown>[],
    vectorize = true,
  ): Promise<{ status: string; items_imported: number; vectors_indexed: number }> {
    return this.request(`/platform/tenants/${slug}/items/import`, {
      method: "POST",
      body: JSON.stringify({ items, vectorize }),
    });
  }

  async deleteMyTenantItem(slug: string, itemId: string): Promise<void> {
    return this.request<void>(`/platform/tenants/${slug}/items/${itemId}`, {
      method: "DELETE",
    });
  }

  // ── Legacy Admin (backward compat) ──

  async getStatus(): Promise<SystemStatus> {
    return this.request<SystemStatus>("/admin/status");
  }

  async getMetrics(): Promise<PlatformMetrics> {
    return this.request<PlatformMetrics>("/admin/metrics");
  }

  async listTenants(): Promise<TenantListResponse> {
    return this.request<TenantListResponse>("/admin/tenants");
  }

  async getTenant(slug: string): Promise<Tenant> {
    return this.request<Tenant>(`/admin/tenants/${slug}`);
  }

  async createTenant(data: CreateTenantRequest): Promise<Tenant> {
    return this.request<Tenant>("/admin/tenants", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async updateTenant(slug: string, data: UpdateTenantRequest): Promise<Tenant> {
    return this.request<Tenant>(`/admin/tenants/${slug}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  }

  async deleteTenant(slug: string): Promise<void> {
    return this.request<void>(`/admin/tenants/${slug}`, {
      method: "DELETE",
    });
  }

  async regenerateKey(slug: string): Promise<Tenant> {
    return this.request<Tenant>(`/admin/tenants/${slug}/regenerate-key`, {
      method: "POST",
    });
  }

  async getTenantStats(slug: string): Promise<TenantStats> {
    return this.request<TenantStats>(`/admin/tenants/${slug}/stats`);
  }

  async listItems(tenantApiKey: string, limit = 100, offset = 0): Promise<ItemsListResponse> {
    return this.request<ItemsListResponse>(`/tenant/items?limit=${limit}&offset=${offset}`, {
      headers: { "X-API-Key": tenantApiKey },
    });
  }

  async deleteItem(tenantApiKey: string, itemId: string): Promise<void> {
    return this.request<void>(`/tenant/items/${itemId}`, {
      method: "DELETE",
      headers: { "X-API-Key": tenantApiKey },
    });
  }

  async importItems(
    tenantApiKey: string,
    items: Record<string, unknown>[],
    vectorize = true,
  ): Promise<{ status: string; items_imported: number; vectors_indexed: number }> {
    return this.request(`/tenant/items/import`, {
      method: "POST",
      headers: { "X-API-Key": tenantApiKey },
      body: JSON.stringify({ items, vectorize }),
    });
  }
}

export const apiClient = new ApiClient();
