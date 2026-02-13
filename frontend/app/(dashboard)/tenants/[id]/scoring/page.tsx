'use client'

import { motion } from 'framer-motion'
import Link from 'next/link'
import { use } from 'react'
import { ArrowLeftIcon } from '@heroicons/react/24/outline'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'

export default function ScoringConfigPage({ params }: { params: Promise<{ id: string }> }) {
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
            <h1 className="text-3xl font-bold text-gray-900">Scoring Configuration</h1>
            <p className="text-gray-500">Configure scoring criteria and weights for this tenant</p>
          </div>
          <Button>Save Configuration</Button>
        </div>

        <Card>
          <p className="text-gray-500 text-center py-12">
            Scoring configuration editor will be implemented in the next phase.
            <br />
            <span className="text-sm">This will include drag-and-drop weight sliders, criteria management, and version history.</span>
          </p>
        </Card>
      </motion.div>
    </div>
  )
}
