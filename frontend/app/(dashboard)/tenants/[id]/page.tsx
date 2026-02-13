'use client'

import { motion } from 'framer-motion'
import Link from 'next/link'
import { use } from 'react'
import {
  ArrowLeftIcon,
  Cog6ToothIcon,
  CubeIcon,
  ChartBarIcon,
} from '@heroicons/react/24/outline'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'

export default function TenantDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)

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
      >
        {/* Tenant Header */}
        <div className="flex items-start justify-between mb-8">
          <div className="flex items-center space-x-4">
            <div className="w-14 h-14 bg-gradient-shazam rounded-xl flex items-center justify-center text-white text-2xl font-bold shadow-shazam">
              T
            </div>
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Tenant Details</h1>
              <p className="text-gray-500">ID: {id}</p>
            </div>
          </div>
          <Badge variant="success" size="md">Active</Badge>
        </div>

        {/* Quick Links */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          <Link href={`/tenants/${id}/scoring`}>
            <Card hover className="flex items-center space-x-4">
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
            <Card hover className="flex items-center space-x-4">
              <div className="w-10 h-10 bg-blue-50 rounded-lg flex items-center justify-center">
                <CubeIcon className="h-5 w-5 text-blue-600" />
              </div>
              <div>
                <h3 className="font-medium text-gray-900">Products</h3>
                <p className="text-sm text-gray-500">Upload & manage products</p>
              </div>
            </Card>
          </Link>
          <Card hover className="flex items-center space-x-4">
            <div className="w-10 h-10 bg-amber-50 rounded-lg flex items-center justify-center">
              <ChartBarIcon className="h-5 w-5 text-amber-600" />
            </div>
            <div>
              <h3 className="font-medium text-gray-900">Analytics</h3>
              <p className="text-sm text-gray-500">View scores & metrics</p>
            </div>
          </Card>
        </div>

        {/* Stats placeholder */}
        <Card>
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Tenant Statistics</h2>
          <p className="text-gray-500 text-sm">
            Connect to the backend API to see live tenant statistics and metrics.
          </p>
        </Card>
      </motion.div>
    </div>
  )
}
