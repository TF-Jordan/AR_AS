import type {
  Tenant,
  TenantListResponse,
  TenantStats,
  PlatformMetrics,
  SystemStatus,
  ItemsListResponse,
  CreateTenantRequest,
  UpdateTenantRequest,
} from "@/types/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

class ApiClient {
  private adminKey: string;

  constructor() {
    this.adminKey = "";
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

  // System
  async getStatus(): Promise<SystemStatus> {
    return this.request<SystemStatus>("/admin/status");
  }

  async getMetrics(): Promise<PlatformMetrics> {
    return this.request<PlatformMetrics>("/admin/metrics");
  }

  // Tenants
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

  // Items (uses tenant API key, not admin key)
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
