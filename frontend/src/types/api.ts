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
