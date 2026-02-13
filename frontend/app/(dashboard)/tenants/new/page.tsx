'use client'

import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeftIcon } from '@heroicons/react/24/outline'
import { TenantForm } from '@/components/tenants/TenantForm'
import { useCreateTenant } from '@/hooks/useTenants'
import type { CreateTenantPayload } from '@/lib/types'

export default function CreateTenantPage() {
  const router = useRouter()
  const createTenant = useCreateTenant()

  const handleSubmit = (data: CreateTenantPayload) => {
    createTenant.mutate(data, {
      onSuccess: (tenant) => {
        router.push(`/tenants/${tenant.id}`)
      },
    })
  }

  return (
    <div className="max-w-2xl mx-auto">
      {/* Back link */}
      <Link
        href="/tenants"
        className="inline-flex items-center text-sm text-gray-500 hover:text-shazam-600 mb-6 transition-colors"
      >
        <ArrowLeftIcon className="h-4 w-4 mr-1" />
        Back to Tenants
      </Link>

      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Create New Tenant</h1>
        <p className="text-gray-500">Set up a new organization on the platform</p>
      </div>

      <TenantForm mode="create" onSubmit={handleSubmit} isSubmitting={createTenant.isPending} />
    </div>
  )
}
