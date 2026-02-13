'use client'

import { motion } from 'framer-motion'
import Link from 'next/link'
import { ArrowLeftIcon } from '@heroicons/react/24/outline'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Input, Textarea } from '@/components/ui/Input'

export default function CreateTenantPage() {
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

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Create New Tenant</h1>
        <p className="text-gray-500 mb-8">Set up a new organization on the platform</p>

        <Card>
          <form className="space-y-6">
            <Input
              label="Tenant Name"
              placeholder="e.g., Acme Corporation"
              helperText="The display name for this organization"
            />
            <Input
              label="Slug"
              placeholder="e.g., acme-corp"
              helperText="URL-friendly identifier (auto-generated from name)"
            />
            <Input
              label="Domain"
              placeholder="e.g., acme.example.com"
              helperText="Optional custom domain for this tenant"
            />
            <Textarea
              label="Description"
              placeholder="Brief description of this tenant..."
              rows={3}
            />

            <div className="flex items-center justify-end space-x-3 pt-4 border-t border-gray-100">
              <Link href="/tenants">
                <Button variant="secondary">Cancel</Button>
              </Link>
              <Button type="submit">Create Tenant</Button>
            </div>
          </form>
        </Card>
      </motion.div>
    </div>
  )
}
