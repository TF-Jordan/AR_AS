'use client'

import { useState } from 'react'
import { Modal } from '@/components/ui/Modal'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Badge } from '@/components/ui/Badge'
import { ScoringCriterion } from '@/lib/types'

interface AddCriterionModalProps {
  isOpen: boolean
  onClose: () => void
  onAdd: (criterion: ScoringCriterion) => void
  existingNames: string[]
}

const SYSTEM_CRITERIA = [
  {
    name: 'similarity',
    description: 'Cosine similarity score from vector search',
  },
  {
    name: 'sentiment_boost',
    description: 'Boost based on sentiment analysis (positive/neutral/negative)',
  },
  {
    name: 'recency',
    description: 'Boost recently added products',
  },
  {
    name: 'popularity',
    description: 'Boost products with high engagement',
  },
]

export const AddCriterionModal = ({
  isOpen,
  onClose,
  onAdd,
  existingNames,
}: AddCriterionModalProps) => {
  const [type, setType] = useState<'system' | 'custom'>('system')
  const [selectedSystem, setSelectedSystem] = useState('')
  const [customName, setCustomName] = useState('')
  const [weight, setWeight] = useState(0.1)
  const [error, setError] = useState('')

  const availableSystemCriteria = SYSTEM_CRITERIA.filter(
    (c) => !existingNames.includes(c.name)
  )

  const handleAdd = () => {
    setError('')

    const name = type === 'system' ? selectedSystem : customName.trim()

    if (!name) {
      setError('Please select or enter a criterion name')
      return
    }

    if (existingNames.includes(name)) {
      setError('This criterion already exists')
      return
    }

    if (type === 'custom' && !/^[a-z_]+$/.test(name)) {
      setError('Custom criterion name must be lowercase letters and underscores only')
      return
    }

    onAdd({
      name,
      type,
      weight,
    })

    // Reset form
    setSelectedSystem('')
    setCustomName('')
    setWeight(0.1)
    setError('')
    onClose()
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Add Scoring Criterion">
      <div className="space-y-4">
        {/* Type selector */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Criterion Type
          </label>
          <div className="grid grid-cols-2 gap-3">
            <button
              onClick={() => setType('system')}
              className={`p-3 rounded-lg border-2 transition-all ${
                type === 'system'
                  ? 'border-shazam-500 bg-shazam-50'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
            >
              <Badge variant="shazam" className="mb-1">
                System
              </Badge>
              <p className="text-xs text-gray-600">Built-in scoring criteria</p>
            </button>
            <button
              onClick={() => setType('custom')}
              className={`p-3 rounded-lg border-2 transition-all ${
                type === 'custom'
                  ? 'border-shazam-500 bg-shazam-50'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
            >
              <Badge variant="default" className="mb-1">
                Custom
              </Badge>
              <p className="text-xs text-gray-600">Product metadata field</p>
            </button>
          </div>
        </div>

        {/* System criterion selector */}
        {type === 'system' && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Select System Criterion
            </label>
            <div className="space-y-2">
              {availableSystemCriteria.length === 0 ? (
                <p className="text-sm text-gray-500 italic">
                  All system criteria are already added
                </p>
              ) : (
                availableSystemCriteria.map((criterion) => (
                  <button
                    key={criterion.name}
                    onClick={() => setSelectedSystem(criterion.name)}
                    className={`w-full p-3 rounded-lg border text-left transition-all ${
                      selectedSystem === criterion.name
                        ? 'border-shazam-500 bg-shazam-50'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <div className="font-medium text-gray-900">{criterion.name}</div>
                    <div className="text-sm text-gray-600">{criterion.description}</div>
                  </button>
                ))
              )}
            </div>
          </div>
        )}

        {/* Custom criterion input */}
        {type === 'custom' && (
          <Input
            label="Field Name"
            value={customName}
            onChange={(e) => setCustomName(e.target.value)}
            placeholder="e.g., price_score, location_match"
            helperText="Must match a field in your product metadata"
          />
        )}

        {/* Initial weight */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Initial Weight: {Math.round(weight * 100)}%
          </label>
          <input
            type="range"
            min="0"
            max="100"
            value={weight * 100}
            onChange={(e) => setWeight(parseInt(e.target.value) / 100)}
            className="w-full"
          />
          <p className="text-xs text-gray-500 mt-1">
            You can adjust weights after adding the criterion
          </p>
        </div>

        {/* Error message */}
        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-600">{error}</p>
          </div>
        )}

        {/* Actions */}
        <div className="flex justify-end gap-3 pt-4">
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={handleAdd}
            disabled={
              (type === 'system' && !selectedSystem) ||
              (type === 'custom' && !customName.trim())
            }
          >
            Add Criterion
          </Button>
        </div>
      </div>
    </Modal>
  )
}
