'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { tenantsApi } from '@/lib/api'
import type { CreateTenantPayload, UpdateTenantPayload } from '@/lib/types'
import toast from 'react-hot-toast'

export function useTenants(params?: { page?: number; page_size?: number; search?: string }) {
  return useQuery({
    queryKey: ['tenants', params],
    queryFn: () => tenantsApi.list(params).then((res) => res.data),
  })
}

export function useTenant(id: string) {
  return useQuery({
    queryKey: ['tenant', id],
    queryFn: () => tenantsApi.get(id).then((res) => res.data),
    enabled: !!id,
  })
}

export function useTenantStats(id: string) {
  return useQuery({
    queryKey: ['tenant-stats', id],
    queryFn: () => tenantsApi.stats(id).then((res) => res.data),
    enabled: !!id,
  })
}

export function useCreateTenant() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: CreateTenantPayload) => tenantsApi.create(data).then((res) => res.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tenants'] })
      toast.success('Tenant created successfully!')
    },
    onError: () => {
      toast.error('Failed to create tenant')
    },
  })
}

export function useUpdateTenant(id: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: UpdateTenantPayload) => tenantsApi.update(id, data).then((res) => res.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tenants'] })
      queryClient.invalidateQueries({ queryKey: ['tenant', id] })
      toast.success('Tenant updated successfully!')
    },
    onError: () => {
      toast.error('Failed to update tenant')
    },
  })
}

export function useDeleteTenant() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => tenantsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tenants'] })
      toast.success('Tenant deleted successfully!')
    },
    onError: () => {
      toast.error('Failed to delete tenant')
    },
  })
}
