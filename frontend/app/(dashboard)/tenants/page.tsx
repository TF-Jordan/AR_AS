'use client'

import { motion } from 'framer-motion'
import Link from 'next/link'
import { PlusIcon, MagnifyingGlassIcon } from '@heroicons/react/24/outline'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'

// Placeholder data - will be replaced with API calls
const mockTenants = [
  { id: '1', name: 'Acme Corp', slug: 'acme-corp', is_active: true, created_at: '2024-01-15', stats: { total_products: 150, total_reviews: 1200, avg_score: 4.2 } },
  { id: '2', name: 'TechStart Inc', slug: 'techstart', is_active: true, created_at: '2024-02-20', stats: { total_products: 75, total_reviews: 580, avg_score: 3.8 } },
  { id: '3', name: 'Global Retail', slug: 'global-retail', is_active: false, created_at: '2024-03-10', stats: { total_products: 320, total_reviews: 2400, avg_score: 4.5 } },
]

export default function TenantsListPage() {
  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Tenants</h1>
          <p className="mt-1 text-gray-500">Manage your multi-tenant organizations</p>
        </div>
        <Link href="/tenants/new">
          <Button>
            <PlusIcon className="h-5 w-5 mr-2" />
            New Tenant
          </Button>
        </Link>
      </div>

      {/* Search Bar */}
      <div className="mb-6">
        <div className="relative max-w-md">
          <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
          <input
            type="text"
            placeholder="Search tenants..."
            className="w-full pl-10 pr-4 py-2.5 rounded-lg border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-shazam-500/20 focus:border-shazam-500 transition-all"
          />
        </div>
      </div>

      {/* Tenants Grid */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
      >
        {mockTenants.map((tenant, i) => (
          <motion.div
            key={tenant.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
          >
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
              </Card>
            </Link>
          </motion.div>
        ))}
      </motion.div>
    </div>
  )
}
