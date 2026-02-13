'use client'

import Link from 'next/link'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import type { Tenant } from '@/lib/types'
import { formatDate } from '@/lib/utils'

interface TenantCardProps {
  tenant: Tenant
}

export function TenantCard({ tenant }: TenantCardProps) {
  return (
    <Link href={`/tenants/${tenant.id}`}>
      <Card hover className="relative overflow-hidden">
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-gradient-shazam rounded-lg flex items-center justify-center text-white font-bold shadow-shazam">
              {tenant.name[0]}
            </div>
            <div>
              <h3 className="font-semibold text-gray-900">{tenant.name}</h3>
              <p className="text-sm text-gray-500">{tenant.slug}</p>
            </div>
          </div>
          <Badge variant={tenant.is_active ? 'success' : 'danger'}>
            {tenant.is_active ? 'Active' : 'Inactive'}
          </Badge>
        </div>

        {tenant.stats && (
          <div className="grid grid-cols-3 gap-4 mt-4 pt-4 border-t border-gray-50">
            <div>
              <p className="text-xs text-gray-500">Products</p>
              <p className="text-lg font-semibold text-gray-900">{tenant.stats.total_products}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Reviews</p>
              <p className="text-lg font-semibold text-gray-900">{tenant.stats.total_reviews}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Avg Score</p>
              <p className="text-lg font-semibold text-shazam-600">{tenant.stats.avg_score}</p>
            </div>
          </div>
        )}

        <p className="text-xs text-gray-400 mt-3">Created {formatDate(tenant.created_at)}</p>
      </Card>
    </Link>
  )
}
