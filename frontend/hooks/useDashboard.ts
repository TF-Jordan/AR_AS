'use client'

import { useQuery } from '@tanstack/react-query'
import { dashboardApi } from '@/lib/api'

export function useDashboardMetrics() {
  return useQuery({
    queryKey: ['dashboard-metrics'],
    queryFn: () => dashboardApi.metrics().then((res) => res.data),
    refetchInterval: 30000, // Refresh every 30 seconds
  })
}
