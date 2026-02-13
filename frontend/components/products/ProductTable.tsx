'use client'

import { motion } from 'framer-motion'
import { Badge } from '@/components/ui/Badge'
import { Card } from '@/components/ui/Card'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { Button } from '@/components/ui/Button'
import { ChevronLeftIcon, ChevronRightIcon } from '@heroicons/react/24/outline'
import type { Product } from '@/lib/types'

interface ProductTableProps {
  products: Product[] | undefined
  isLoading?: boolean
  page?: number
  totalPages?: number
  onPageChange?: (page: number) => void
}

export const ProductTable = ({
  products,
  isLoading,
  page = 1,
  totalPages = 1,
  onPageChange,
}: ProductTableProps) => {
  if (isLoading) {
    return (
      <Card className="flex items-center justify-center py-12">
        <LoadingSpinner />
      </Card>
    )
  }

  if (!products || products.length === 0) {
    return (
      <Card className="text-center py-12">
        <p className="text-gray-500 mb-2">No products found</p>
        <p className="text-sm text-gray-400">Upload your first CSV file to get started</p>
      </Card>
    )
  }

  const hasNextPage = page < totalPages
  const hasPrevPage = page > 1

  return (
    <div className="space-y-4">
      <Card className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Product
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  SKU
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Category
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Score
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Reviews
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Created
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {products.map((product, index) => (
                <motion.tr
                  key={product.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.03 }}
                  className="hover:bg-gray-50 transition-colors"
                >
                  <td className="px-6 py-4">
                    <div>
                      <p className="font-medium text-gray-900">{product.name}</p>
                      {product.description && (
                        <p className="text-sm text-gray-500 line-clamp-1 max-w-md">
                          {product.description}
                        </p>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {product.sku ? (
                      <code className="text-sm text-gray-700 bg-gray-100 px-2 py-1 rounded">
                        {product.sku}
                      </code>
                    ) : (
                      <span className="text-gray-400 text-sm">—</span>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {product.category ? (
                      <Badge variant="default">{product.category}</Badge>
                    ) : (
                      <span className="text-gray-400 text-sm">—</span>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {product.score ? (
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-shazam-600">
                          {product.score.toFixed(2)}
                        </span>
                        <div className="w-16 h-2 bg-gray-200 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-gradient-shazam"
                            style={{ width: `${product.score * 100}%` }}
                          />
                        </div>
                      </div>
                    ) : (
                      <span className="text-gray-400 text-sm">Not scored</span>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">
                    {product.review_count.toLocaleString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {new Date(product.created_at).toLocaleDateString('en-US', {
                      month: 'short',
                      day: 'numeric',
                      year: 'numeric',
                    })}
                  </td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Pagination */}
      {totalPages > 1 && onPageChange && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-gray-500">
            Page {page} of {totalPages}
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={() => onPageChange(page - 1)}
              disabled={!hasPrevPage}
              size="sm"
            >
              <ChevronLeftIcon className="h-4 w-4 mr-1" />
              Previous
            </Button>
            <Button
              variant="outline"
              onClick={() => onPageChange(page + 1)}
              disabled={!hasNextPage}
              size="sm"
            >
              Next
              <ChevronRightIcon className="h-4 w-4 ml-1" />
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
