'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import Link from 'next/link'
import { use } from 'react'
import { ArrowLeftIcon, CubeIcon } from '@heroicons/react/24/outline'
import { Card } from '@/components/ui/Card'
import { ProductUploader } from '@/components/products/ProductUploader'
import { ProductTable } from '@/components/products/ProductTable'
import { useProducts, useUploadProducts } from '@/hooks/useProducts'
import { useTenant } from '@/hooks/useTenants'

export default function ProductsPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const [page, setPage] = useState(1)
  const [uploadResult, setUploadResult] = useState<any>(null)

  const { data: tenant } = useTenant(id)
  const { data: productsData, isLoading } = useProducts(id, { page, page_size: 20 })
  const uploadMutation = useUploadProducts(id)

  const handleUpload = (file: File) => {
    uploadMutation.mutate(file, {
      onSuccess: (result) => {
        setUploadResult(result)
      },
      onError: () => {
        setUploadResult({
          success: false,
          total_processed: 0,
          total_created: 0,
          total_updated: 0,
          errors: ['Upload failed. Please try again.'],
        })
      },
    })
  }

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
        className="space-y-6"
      >
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Products</h1>
            <p className="text-gray-500">
              Manage products for{' '}
              <span className="font-semibold">{tenant?.name || id}</span>
              {productsData && (
                <span className="ml-2 text-shazam-600 font-medium">
                  ({productsData.total} total)
                </span>
              )}
            </p>
          </div>
          <ProductUploader
            onUpload={handleUpload}
            isUploading={uploadMutation.isPending}
            result={uploadResult}
          />
        </div>

        {/* Stats Overview */}
        {productsData && productsData.total > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-shazam-100 rounded-lg flex items-center justify-center">
                <CubeIcon className="h-5 w-5 text-shazam-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">Total Products</p>
                <p className="text-xl font-bold text-gray-900">
                  {productsData.total.toLocaleString()}
                </p>
              </div>
            </Card>
            <Card className="flex items-center space-x-3">
              <div>
                <p className="text-sm text-gray-500">Current Page</p>
                <p className="text-xl font-bold text-gray-900">
                  {productsData.page} / {productsData.total_pages}
                </p>
              </div>
            </Card>
            <Card className="flex items-center space-x-3">
              <div>
                <p className="text-sm text-gray-500">Showing</p>
                <p className="text-xl font-bold text-gray-900">
                  {productsData.items.length}
                </p>
              </div>
            </Card>
            <Card className="flex items-center space-x-3">
              <div>
                <p className="text-sm text-gray-500">Per Page</p>
                <p className="text-xl font-bold text-gray-900">
                  {productsData.page_size}
                </p>
              </div>
            </Card>
          </div>
        )}

        {/* Products Table */}
        <ProductTable
          products={productsData?.items}
          isLoading={isLoading}
          page={productsData?.page}
          totalPages={productsData?.total_pages}
          onPageChange={setPage}
        />
      </motion.div>
    </div>
  )
}
