// ============================================================
// RaaS Platform TypeScript Types
// ============================================================

// Auth types
export interface User {
  id: string
  email: string
  name: string
  role: 'admin' | 'tenant_admin' | 'user'
}

export interface AuthSession {
  user: User
  accessToken: string
  idToken?: string
}

// Tenant types
export interface Tenant {
  id: string
  name: string
  slug: string
  domain?: string
  is_active: boolean
  created_at: string
  updated_at: string
  settings?: TenantSettings
  stats?: TenantStats
}

export interface TenantSettings {
  branding?: {
    primary_color?: string
    logo_url?: string
  }
  features?: Record<string, boolean>
}

export interface TenantStats {
  total_products: number
  total_reviews: number
  total_scores: number
  avg_score: number
  active_users: number
}

export interface CreateTenantPayload {
  name: string
  slug: string
  domain?: string
  is_active?: boolean
  settings?: TenantSettings
}

export interface UpdateTenantPayload {
  name?: string
  domain?: string
  is_active?: boolean
  settings?: TenantSettings
}

// Scoring types
export interface ScoringCriterion {
  name: string
  type: 'system' | 'custom'
  weight: number
}

export interface ScoringConfig {
  id: string
  tenant_id: string
  version: number
  criteria: ScoringCriterion[]
  aggregation_method: 'weighted_average' | 'simple_average' | 'custom'
  created_at: string
  updated_at: string
  is_active: boolean
}

export interface ScoringConfigHistory {
  configs: ScoringConfig[]
  total: number
}

// Product types
export interface Product {
  id: string
  tenant_id: string
  name: string
  sku?: string
  category?: string
  description?: string
  score?: number
  review_count: number
  created_at: string
  updated_at: string
}

export interface ProductUploadResult {
  success: boolean
  total_processed: number
  total_created: number
  total_updated: number
  errors: string[]
}

export interface ProductStats {
  total_products: number
  categories: { name: string; count: number }[]
  avg_score: number
}

// API Response types
export interface ApiResponse<T> {
  data: T
  message?: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface ApiError {
  detail: string
  status_code: number
}

// Dashboard types
export interface DashboardMetrics {
  total_tenants: number
  active_tenants: number
  total_products: number
  total_reviews: number
  avg_score?: number
  tenants_growth?: string
  products_growth?: string
  reviews_growth?: string
  score_growth?: string
  recent_activity: ActivityItem[]
}

export interface ActivityItem {
  id: string
  type: 'tenant_created' | 'config_updated' | 'products_uploaded' | 'score_calculated'
  message: string
  timestamp: string
  tenant_name?: string
}
