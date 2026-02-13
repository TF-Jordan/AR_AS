'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { scoringApi } from '@/lib/api'
import { ScoringConfig, ScoringCriterion } from '@/lib/types'
import toast from 'react-hot-toast'

export const useScoring = (tenantId: string) => {
  const queryClient = useQueryClient()

  const getConfig = useQuery({
    queryKey: ['scoring', tenantId],
    queryFn: () => scoringApi.getConfig(tenantId),
    enabled: !!tenantId,
  })

  const getHistory = useQuery({
    queryKey: ['scoring-history', tenantId],
    queryFn: () => scoringApi.getHistory(tenantId),
    enabled: !!tenantId,
  })

  const updateConfig = useMutation({
    mutationFn: (criteria: ScoringCriterion[]) =>
      scoringApi.updateConfig(tenantId, { criteria }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scoring', tenantId] })
      queryClient.invalidateQueries({ queryKey: ['scoring-history', tenantId] })
      toast.success('Scoring configuration updated successfully!')
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.error?.message || 'Failed to update scoring configuration')
    },
  })

  return {
    config: getConfig.data?.data,
    history: getHistory.data?.data,
    isLoading: getConfig.isLoading,
    isUpdating: updateConfig.isPending,
    updateConfig: updateConfig.mutate,
    refetch: getConfig.refetch,
  }
}
