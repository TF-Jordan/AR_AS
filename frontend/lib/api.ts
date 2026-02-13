import axios from 'axios'
import type {
  Tenant,
  CreateTenantPayload,
  UpdateTenantPayload,
  TenantStats,
  ScoringConfig,
  ScoringConfigHistory,
  ProductUploadResult,
  ProductStats,
  PaginatedResponse,
  Product,
  DashboardMetrics,
} from './types'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add auth token to all requests
api.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
  }
  return config
})

// Handle response errors globally
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      if (typeof window !== 'undefined') {
        localStorage.removeItem('access_token')
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

// ============================================================
// Tenant API
// ============================================================
export const tenantsApi = {
  list: (params?: { page?: number; page_size?: number; search?: string }) =>
    api.get<PaginatedResponse<Tenant>>('/admin/tenants/', { params }),

  get: (id: string) =>
    api.get<Tenant>(`/admin/tenants/${id}`),

  create: (data: CreateTenantPayload) =>
    api.post<Tenant>('/admin/tenants/', data),

  update: (id: string, data: UpdateTenantPayload) =>
    api.patch<Tenant>(`/admin/tenants/${id}`, data),

  delete: (id: string) =>
    api.delete(`/admin/tenants/${id}`),

  stats: (id: string) =>
    api.get<TenantStats>(`/admin/tenants/${id}/stats`),
}

// ============================================================
// Scoring API
// ============================================================
export const scoringApi = {
  getConfig: (tenantId: string) =>
    api.get<ScoringConfig>(`/admin/scoring/tenants/${tenantId}/config`),

  updateConfig: (tenantId: string, data: Partial<ScoringConfig>) =>
    api.put<ScoringConfig>(`/admin/scoring/tenants/${tenantId}/config`, data),

  getHistory: (tenantId: string) =>
    api.get<ScoringConfigHistory>(`/admin/scoring/tenants/${tenantId}/config/history`),
}

// ============================================================
// Products API
// ============================================================
export const productsApi = {
  list: (tenantId: string, params?: { page?: number; page_size?: number }) =>
    api.get<PaginatedResponse<Product>>(`/tenants/${tenantId}/products`, { params }),

  upload: (tenantId: string, file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post<ProductUploadResult>(`/tenants/${tenantId}/products/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  stats: (tenantId?: string) =>
    api.get<ProductStats>(tenantId ? `/tenants/${tenantId}/products/stats` : '/products/stats'),
}

// ============================================================
// Dashboard API
// ============================================================
export const dashboardApi = {
  metrics: () =>
    api.get<DashboardMetrics>('/admin/dashboard/metrics'),
}
