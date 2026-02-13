'use client'

import { motion } from 'framer-motion'
import Link from 'next/link'
import { use } from 'react'
import {
  ArrowLeftIcon,
  Cog6ToothIcon,
  CubeIcon,
  ChartBarIcon,
  PencilIcon,
} from '@heroicons/react/24/outline'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { TenantStats } from '@/components/tenants/TenantStats'
import { useTenant, useTenantStats } from '@/hooks/useTenants'

export default function TenantDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const { data: tenant, isLoading: tenantLoading } = useTenant(id)
  const { data: stats, isLoading: statsLoading } = useTenantStats(id)

  if (tenantLoading) {
    return <LoadingSpinner />
  }

  if (!tenant) {
    return (
      <div className="text-center py-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Tenant not found</h2>
        <p className="text-gray-500 mb-6">The tenant you&apos;re looking for doesn&apos;t exist.</p>
        <Link href="/tenants">
          <Button variant="primary">Back to Tenants</Button>
        </Link>
      </div>
    )
  }

  return (
    <div>
      {/* Back link */}
      <Link
        href="/tenants"
        className="inline-flex items-center text-sm text-gray-500 hover:text-shazam-600 mb-6 transition-colors"
      >
        <ArrowLeftIcon className="h-4 w-4 mr-1" />
        Back to Tenants
      </Link>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="space-y-8"
      >
        {/* Tenant Header */}
        <div className="flex items-start justify-between">
          <div className="flex items-center space-x-4">
            <div className="w-14 h-14 bg-gradient-shazam rounded-xl flex items-center justify-center text-white text-2xl font-bold shadow-shazam">
              {tenant.name[0].toUpperCase()}
            </div>
            <div>
              <h1 className="text-3xl font-bold text-gray-900">{tenant.name}</h1>
              <div className="flex items-center gap-3 mt-1">
                <p className="text-gray-500">{tenant.slug}</p>
                {tenant.domain && (
                  <>
                    <span className="text-gray-300">•</span>
                    <p className="text-gray-500">{tenant.domain}</p>
                  </>
                )}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Badge variant={tenant.is_active ? 'success' : 'danger'} size="md">
              {tenant.is_active ? 'Active' : 'Inactive'}
            </Badge>
            <Button variant="outline" size="sm">
              <PencilIcon className="h-4 w-4 mr-2" />
              Edit
            </Button>
          </div>
        </div>

        {/* Quick Links */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Link href={`/tenants/${id}/scoring`}>
            <Card hover className="flex items-center space-x-4 h-full">
              <div className="w-10 h-10 bg-shazam-50 rounded-lg flex items-center justify-center">
                <Cog6ToothIcon className="h-5 w-5 text-shazam-600" />
              </div>
              <div>
                <h3 className="font-medium text-gray-900">Scoring Config</h3>
                <p className="text-sm text-gray-500">Configure criteria & weights</p>
              </div>
            </Card>
          </Link>
          <Link href={`/tenants/${id}/products`}>
            <Card hover className="flex items-center space-x-4 h-full">
              <div className="w-10 h-10 bg-blue-50 rounded-lg flex items-center justify-center">
                <CubeIcon className="h-5 w-5 text-blue-600" />
              </div>
              <div>
                <h3 className="font-medium text-gray-900">Products</h3>
                <p className="text-sm text-gray-500">Upload & manage products</p>
              </div>
            </Card>
          </Link>
          <Card hover className="flex items-center space-x-4 h-full">
            <div className="w-10 h-10 bg-amber-50 rounded-lg flex items-center justify-center">
              <ChartBarIcon className="h-5 w-5 text-amber-600" />
            </div>
            <div>
              <h3 className="font-medium text-gray-900">Analytics</h3>
              <p className="text-sm text-gray-500">View scores & metrics</p>
            </div>
          </Card>
        </div>

        {/* Stats */}
        <TenantStats stats={stats} isLoading={statsLoading} />

        {/* Tenant Details */}
        <Card>
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Tenant Details</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <p className="text-sm text-gray-500 mb-1">Tenant ID</p>
              <p className="text-sm font-mono text-gray-900">{tenant.id}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500 mb-1">Slug</p>
              <p className="text-sm font-mono text-gray-900">{tenant.slug}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500 mb-1">Created At</p>
              <p className="text-sm text-gray-900">
                {new Date(tenant.created_at).toLocaleDateString('en-US', {
                  year: 'numeric',
                  month: 'long',
                  day: 'numeric',
                })}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-500 mb-1">Last Updated</p>
              <p className="text-sm text-gray-900">
                {new Date(tenant.updated_at).toLocaleDateString('en-US', {
                  year: 'numeric',
                  month: 'long',
                  day: 'numeric',
                })}
              </p>
            </div>
            {tenant.domain && (
              <div>
                <p className="text-sm text-gray-500 mb-1">Custom Domain</p>
                <p className="text-sm text-gray-900">{tenant.domain}</p>
              </div>
            )}
          </div>
        </Card>
      </motion.div>
    </div>
  )
}
