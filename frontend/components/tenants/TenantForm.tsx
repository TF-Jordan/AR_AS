'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Card } from '@/components/ui/Card'
import { CreateTenantPayload, Tenant } from '@/lib/types'

interface TenantFormProps {
  initialData?: Tenant
  onSubmit: (data: CreateTenantPayload) => void
  isSubmitting?: boolean
  mode: 'create' | 'edit'
}

export const TenantForm = ({ initialData, onSubmit, isSubmitting, mode }: TenantFormProps) => {
  const router = useRouter()
  const [formData, setFormData] = useState<CreateTenantPayload>({
    name: initialData?.name || '',
    slug: initialData?.slug || '',
    domain: initialData?.domain || '',
    is_active: initialData?.is_active ?? true,
  })
  const [errors, setErrors] = useState<Record<string, string>>({})

  // Auto-generate slug from name
  useEffect(() => {
    if (mode === 'create' && formData.name && !formData.slug) {
      const generatedSlug = formData.name
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '-')
        .replace(/^-|-$/g, '')
      setFormData((prev) => ({ ...prev, slug: generatedSlug }))
    }
  }, [formData.name, formData.slug, mode])

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {}

    if (!formData.name.trim()) {
      newErrors.name = 'Tenant name is required'
    } else if (formData.name.length < 3) {
      newErrors.name = 'Name must be at least 3 characters'
    } else if (formData.name.length > 100) {
      newErrors.name = 'Name must be less than 100 characters'
    }

    if (!formData.slug.trim()) {
      newErrors.slug = 'Slug is required'
    } else if (!/^[a-z0-9-]+$/.test(formData.slug)) {
      newErrors.slug = 'Slug must contain only lowercase letters, numbers, and hyphens'
    } else if (formData.slug.length < 3) {
      newErrors.slug = 'Slug must be at least 3 characters'
    } else if (formData.slug.length > 50) {
      newErrors.slug = 'Slug must be less than 50 characters'
    }

    if (formData.domain && !/^[a-z0-9.-]+\.[a-z]{2,}$/.test(formData.domain)) {
      newErrors.domain = 'Invalid domain format (e.g., example.com)'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (validateForm()) {
      onSubmit(formData)
    }
  }

  const handleChange = (field: keyof CreateTenantPayload, value: string | boolean) => {
    setFormData((prev) => ({ ...prev, [field]: value }))
    // Clear error for this field
    if (errors[field]) {
      setErrors((prev) => {
        const newErrors = { ...prev }
        delete newErrors[field]
        return newErrors
      })
    }
  }

  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
      <Card>
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Tenant Name */}
          <Input
            label="Tenant Name"
            value={formData.name}
            onChange={(e) => handleChange('name', e.target.value)}
            placeholder="e.g., Acme Corporation"
            helperText="The display name for this organization"
            error={errors.name}
            disabled={isSubmitting}
            required
          />

          {/* Slug */}
          <Input
            label="Slug"
            value={formData.slug}
            onChange={(e) => handleChange('slug', e.target.value)}
            placeholder="e.g., acme-corp"
            helperText={
              mode === 'create'
                ? 'URL-friendly identifier (auto-generated from name)'
                : 'Cannot be changed after creation'
            }
            error={errors.slug}
            disabled={isSubmitting || mode === 'edit'}
            required
          />

          {/* Domain */}
          <Input
            label="Domain"
            value={formData.domain || ''}
            onChange={(e) => handleChange('domain', e.target.value)}
            placeholder="e.g., acme.example.com"
            helperText="Optional custom domain for this tenant"
            error={errors.domain}
            disabled={isSubmitting}
          />

          {/* Active Status */}
          <div>
            <label className="flex items-center space-x-3 cursor-pointer">
              <input
                type="checkbox"
                checked={formData.is_active}
                onChange={(e) => handleChange('is_active', e.target.checked)}
                disabled={isSubmitting}
                className="w-5 h-5 rounded border-gray-300 text-shazam-600 focus:ring-shazam-500 disabled:opacity-50"
              />
              <div>
                <span className="text-sm font-medium text-gray-700">Active</span>
                <p className="text-xs text-gray-500">
                  Inactive tenants cannot access the platform
                </p>
              </div>
            </label>
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end space-x-3 pt-4 border-t border-gray-100">
            <Button
              type="button"
              variant="secondary"
              onClick={() => router.back()}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button type="submit" variant="primary" disabled={isSubmitting} isLoading={isSubmitting}>
              {mode === 'create' ? 'Create Tenant' : 'Save Changes'}
            </Button>
          </div>
        </form>
      </Card>
    </motion.div>
  )
}
