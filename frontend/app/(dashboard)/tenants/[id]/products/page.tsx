'use client'

import { motion } from 'framer-motion'
import Link from 'next/link'
import { use } from 'react'
import { ArrowLeftIcon, CloudArrowUpIcon } from '@heroicons/react/24/outline'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'

export default function ProductsPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)

  return (
    <div>
      <Link
        href={`/tenants/${id}`}
        className="inline-flex items-center text-sm text-gray-500 hover:text-shazam-600 mb-6 transition-colors"
      >
        <ArrowLeftIcon className="h-4 w-4 mr-1" />
        Back to Tenant
      </Link>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Products</h1>
            <p className="text-gray-500">Upload and manage products for this tenant</p>
          </div>
          <Button>
            <CloudArrowUpIcon className="h-5 w-5 mr-2" />
            Upload Products
          </Button>
        </div>

        <Card>
          <p className="text-gray-500 text-center py-12">
            Product upload and management will be implemented in the next phase.
            <br />
            <span className="text-sm">This will include CSV upload, product table, and batch operations.</span>
          </p>
        </Card>
      </motion.div>
    </div>
  )
}
