export interface ScoringCriterion {
  name: string;
  weight: number;
}

export interface Tenant {
  tenant_id: string;
  name: string;
  slug: string;
  domain: string;
  api_key: string;
  status: string;
  scoring_config: {
    criteria: ScoringCriterion[];
  };
  created_at: string;
  updated_at: string;
}

export interface TenantListResponse {
  tenants: Tenant[];
  total: number;
}

export interface TenantStats {
  tenant: string;
  items_count: number;
  vectors_count: number;
  collection_status: string;
}

export interface PlatformMetrics {
  active_tenants: number;
  total_tenants: number;
  total_items: number;
  total_vectors: number;
  tenant_stats: {
    slug: string;
    items_count: number;
    vectors_count: number;
    error?: string;
  }[];
  services: {
    redis: boolean;
    qdrant: boolean;
    postgresql: boolean;
  };
}

export interface SystemStatus {
  status: string;
  services: Record<string, boolean>;
  error?: string;
}

export interface TenantItem {
  id: string;
  data: Record<string, unknown>;
  embedding_text: string;
  created_at: string;
}

export interface ItemsListResponse {
  items: TenantItem[];
  total: number;
  limit: number;
  offset: number;
  tenant: string;
}

export interface CreateTenantRequest {
  name: string;
  slug: string;
  domain: string;
  scoring: {
    criteria: ScoringCriterion[];
  };
}

export interface UpdateTenantRequest {
  name?: string;
  domain?: string;
  status?: string;
  scoring?: {
    criteria: ScoringCriterion[];
  };
}

// ── Auth types ──

export type UserRole = "super_admin" | "platform_owner";

export interface AuthResponse {
  token: string;
  role: UserRole;
  platform?: {
    slug: string;
    name: string;
    domain: string;
    email: string;
  };
}

export interface PlatformInfo {
  slug: string;
  name: string;
  domain: string;
  email: string;
}

// ── Super Admin types ──

export interface PlatformEntry {
  platform_id: string;
  name: string;
  slug: string;
  domain: string;
  email: string;
  api_key: string;
  is_active: boolean;
  tenants_count: number;
  created_at: string;
  updated_at: string;
  tenants?: {
    tenant_id: string;
    name: string;
    slug: string;
    domain: string;
    status: string;
    created_at: string;
  }[];
}

export interface PlatformListResponse {
  platforms: PlatformEntry[];
  total: number;
}

export interface SuperAdminDashboard {
  total_platforms: number;
  active_platforms: number;
  total_tenants: number;
  active_tenants: number;
  services: Record<string, boolean>;
  event_bus: {
    handlers: number;
    pending_tasks: number;
  };
}

// ── Platform Owner types ──

export interface PlatformDashboard {
  platform_name: string;
  platform_slug: string;
  active_tenants: number;
  total_tenants: number;
  total_items: number;
  total_vectors: number;
  tenant_stats: {
    slug: string;
    items_count: number;
    vectors_count: number;
    error?: string;
  }[];
}
