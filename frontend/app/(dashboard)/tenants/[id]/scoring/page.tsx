'use client'

import { motion } from 'framer-motion'
import Link from 'next/link'
import { use } from 'react'
import { ArrowLeftIcon, ClockIcon } from '@heroicons/react/24/outline'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { ScoringConfigEditor } from '@/components/scoring/ScoringConfigEditor'
import { useScoring } from '@/hooks/useScoring'
import { useTenant } from '@/hooks/useTenants'

export default function ScoringConfigPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const { data: tenant, isLoading: tenantLoading } = useTenant(id)
  const { config, history, isLoading, isUpdating, updateConfig } = useScoring(id)

  if (tenantLoading || isLoading) {
    return <LoadingSpinner />
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
        <div>
          <div className="flex items-center gap-3 mb-2">
            <h1 className="text-3xl font-bold text-gray-900">Scoring Configuration</h1>
            {config && (
              <Badge variant="shazam">Version {config.version}</Badge>
            )}
          </div>
          <p className="text-gray-500">
            Configure scoring criteria and weights for <span className="font-semibold">{tenant?.name || id}</span>
          </p>
        </div>

        {/* Main editor */}
        <ScoringConfigEditor
          initialCriteria={config?.criteria || []}
          onSave={updateConfig}
          isSaving={isUpdating}
        />

        {/* Version history */}
        {history && history.configs && history.configs.length > 1 && (
          <Card className="p-6">
            <div className="flex items-center gap-2 mb-4">
              <ClockIcon className="w-5 h-5 text-gray-400" />
              <h3 className="font-semibold text-gray-900">Version History</h3>
              <Badge variant="info">{history.total} versions</Badge>
            </div>

            <div className="space-y-3">
              {history.configs.slice(0, 5).map((version: any, index: number) => (
                <div
                  key={version.id}
                  className={`flex items-center justify-between p-3 rounded-lg border ${
                    index === 0 ? 'border-shazam-300 bg-shazam-50' : 'border-gray-200'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <Badge variant={index === 0 ? 'shazam' : 'default'}>
                      v{version.version}
                    </Badge>
                    {index === 0 && (
                      <Badge variant="success">Current</Badge>
                    )}
                    <span className="text-sm text-gray-600">
                      {version.criteria.length} criteria
                    </span>
                  </div>
                  <span className="text-sm text-gray-500">
                    {new Date(version.created_at).toLocaleDateString()}
                  </span>
                </div>
              ))}
            </div>

            {history.configs.length > 5 && (
              <p className="text-sm text-gray-500 mt-3 text-center">
                + {history.configs.length - 5} more versions
              </p>
            )}
          </Card>
        )}
      </motion.div>
    </div>
  )
}
