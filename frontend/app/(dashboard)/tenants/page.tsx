'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import Link from 'next/link'
import { PlusIcon, MagnifyingGlassIcon, ChevronLeftIcon, ChevronRightIcon } from '@heroicons/react/24/outline'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { TenantCard } from '@/components/tenants/TenantCard'
import { useTenants } from '@/hooks/useTenants'

export default function TenantsListPage() {
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [searchQuery, setSearchQuery] = useState('')

  const { data, isLoading } = useTenants({
    page,
    page_size: 12,
    search: searchQuery,
  })

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setSearchQuery(search)
    setPage(1) // Reset to first page on new search
  }

  const handleClearSearch = () => {
    setSearch('')
    setSearchQuery('')
    setPage(1)
  }

  const totalPages = data?.total_pages || 1
  const hasNextPage = page < totalPages
  const hasPrevPage = page > 1

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Tenants</h1>
          <p className="mt-1 text-gray-500">
            Manage your multi-tenant organizations
            {data && (
              <span className="ml-2 text-shazam-600 font-medium">
                ({data.total} total)
              </span>
            )}
          </p>
        </div>
        <Link href="/tenants/new">
          <Button variant="primary">
            <PlusIcon className="h-5 w-5 mr-2" />
            New Tenant
          </Button>
        </Link>
      </div>

      {/* Search Bar */}
      <form onSubmit={handleSearch} className="mb-6">
        <div className="flex gap-3 max-w-2xl">
          <div className="relative flex-1">
            <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search tenants by name or slug..."
              className="w-full pl-10 pr-4 py-2.5 rounded-lg border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-shazam-500/20 focus:border-shazam-500 transition-all"
            />
          </div>
          <Button type="submit" variant="primary">
            Search
          </Button>
          {searchQuery && (
            <Button type="button" variant="secondary" onClick={handleClearSearch}>
              Clear
            </Button>
          )}
        </div>
        {searchQuery && (
          <p className="text-sm text-gray-500 mt-2">
            Showing results for &quot;{searchQuery}&quot;
          </p>
        )}
      </form>

      {/* Loading State */}
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <LoadingSpinner />
        </div>
      )}

      {/* Empty State */}
      {!isLoading && data?.items.length === 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-center py-12 border-2 border-dashed border-gray-300 rounded-lg"
        >
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            {searchQuery ? 'No tenants found' : 'No tenants yet'}
          </h3>
          <p className="text-gray-500 mb-6">
            {searchQuery
              ? 'Try adjusting your search query'
              : 'Get started by creating your first tenant'}
          </p>
          {!searchQuery && (
            <Link href="/tenants/new">
              <Button variant="primary">
                <PlusIcon className="h-5 w-5 mr-2" />
                Create First Tenant
              </Button>
            </Link>
          )}
        </motion.div>
      )}

      {/* Tenants Grid */}
      {!isLoading && data && data.items.length > 0 && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8"
          >
            {data.items.map((tenant, i) => (
              <motion.div
                key={tenant.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05 }}
              >
                <TenantCard tenant={tenant} />
              </motion.div>
            ))}
          </motion.div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between">
              <p className="text-sm text-gray-500">
                Page {page} of {totalPages}
              </p>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={!hasPrevPage}
                >
                  <ChevronLeftIcon className="h-5 w-5" />
                  Previous
                </Button>
                <Button
                  variant="outline"
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={!hasNextPage}
                >
                  Next
                  <ChevronRightIcon className="h-5 w-5 ml-1" />
                </Button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
