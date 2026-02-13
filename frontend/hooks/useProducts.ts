'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { productsApi } from '@/lib/api'
import toast from 'react-hot-toast'

export function useProducts(tenantId: string, params?: { page?: number; page_size?: number }) {
  return useQuery({
    queryKey: ['products', tenantId, params],
    queryFn: () => productsApi.list(tenantId, params).then((res) => res.data),
    enabled: !!tenantId,
  })
}

export function useProductStats(tenantId?: string) {
  return useQuery({
    queryKey: ['product-stats', tenantId],
    queryFn: () => productsApi.stats(tenantId).then((res) => res.data),
  })
}

export function useUploadProducts(tenantId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (file: File) => productsApi.upload(tenantId, file).then((res) => res.data),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['products', tenantId] })
      queryClient.invalidateQueries({ queryKey: ['product-stats'] })
      toast.success(`Uploaded ${data.total_created} products successfully!`)
    },
    onError: () => {
      toast.error('Failed to upload products')
    },
  })
}
