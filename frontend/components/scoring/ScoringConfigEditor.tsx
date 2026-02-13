'use client'

import { useState, useEffect } from 'react'
import { DragDropContext, Droppable, DropResult } from '@hello-pangea/dnd'
import { motion, AnimatePresence } from 'framer-motion'
import { PlusIcon, ArrowPathIcon, CheckCircleIcon, ExclamationCircleIcon } from '@heroicons/react/24/outline'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { CriterionRow } from './CriterionRow'
import { AddCriterionModal } from './AddCriterionModal'
import { ScoringCriterion } from '@/lib/types'

interface ScoringConfigEditorProps {
  initialCriteria?: ScoringCriterion[]
  onSave: (criteria: ScoringCriterion[]) => void
  isSaving?: boolean
}

export const ScoringConfigEditor = ({
  initialCriteria = [
    { name: 'similarity', type: 'system', weight: 0.7 },
    { name: 'sentiment_boost', type: 'system', weight: 0.2 },
    { name: 'price_score', type: 'custom', weight: 0.1 },
  ],
  onSave,
  isSaving,
}: ScoringConfigEditorProps) => {
  const [criteria, setCriteria] = useState<ScoringCriterion[]>(initialCriteria)
  const [isAddModalOpen, setIsAddModalOpen] = useState(false)
  const [hasChanges, setHasChanges] = useState(false)

  // Calculate total weight
  const totalWeight = criteria.reduce((sum, c) => sum + c.weight, 0)
  const isValid = Math.abs(totalWeight - 1.0) < 0.01 // 1% tolerance

  useEffect(() => {
    // Check if criteria changed from initial
    const changed = JSON.stringify(criteria) !== JSON.stringify(initialCriteria)
    setHasChanges(changed)
  }, [criteria, initialCriteria])

  const handleDragEnd = (result: DropResult) => {
    if (!result.destination) return

    const items = Array.from(criteria)
    const [reorderedItem] = items.splice(result.source.index, 1)
    items.splice(result.destination.index, 0, reorderedItem)

    setCriteria(items)
  }

  const handleWeightChange = (index: number, newWeight: number) => {
    const updated = [...criteria]
    updated[index] = { ...updated[index], weight: newWeight }
    setCriteria(updated)
  }

  const handleDelete = (index: number) => {
    if (criteria.length === 1) {
      alert('You must have at least one criterion')
      return
    }
    const updated = criteria.filter((_, i) => i !== index)
    setCriteria(updated)
  }

  const handleAdd = (newCriterion: ScoringCriterion) => {
    setCriteria([...criteria, newCriterion])
  }

  const handleReset = () => {
    if (confirm('Reset to initial configuration?')) {
      setCriteria(initialCriteria)
    }
  }

  const handleAutoBalance = () => {
    // Redistribute weights evenly
    const weight = 1.0 / criteria.length
    const balanced = criteria.map(c => ({ ...c, weight }))
    setCriteria(balanced)
  }

  const handleSave = () => {
    if (!isValid) {
      alert('Weights must sum to 100% before saving')
      return
    }
    onSave(criteria)
  }

  return (
    <div className="space-y-6">
      {/* Header with validation status */}
      <Card variant="shazam" className="p-6">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-white mb-1">
              Scoring Configuration
            </h3>
            <p className="text-shazam-100 text-sm">
              Drag to reorder, adjust weights, add custom criteria
            </p>
          </div>
          <div className="flex items-center gap-3">
            {/* Total weight indicator */}
            <div className={`flex items-center gap-2 px-4 py-2 rounded-lg ${
              isValid ? 'bg-green-500/20 text-green-100' : 'bg-red-500/20 text-red-100'
            }`}>
              {isValid ? (
                <CheckCircleIcon className="w-5 h-5" />
              ) : (
                <ExclamationCircleIcon className="w-5 h-5" />
              )}
              <span className="font-bold">{Math.round(totalWeight * 100)}%</span>
            </div>

            {/* Criteria count */}
            <Badge variant="info">
              {criteria.length} {criteria.length === 1 ? 'criterion' : 'criteria'}
            </Badge>
          </div>
        </div>

        {/* Validation message */}
        {!isValid && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-4 p-3 bg-red-500/20 border border-red-300 rounded-lg"
          >
            <p className="text-sm text-red-100">
              ⚠️ Weights must sum to exactly 100%. Current total: {Math.round(totalWeight * 100)}%
            </p>
          </motion.div>
        )}
      </Card>

      {/* Action buttons */}
      <div className="flex items-center justify-between">
        <div className="flex gap-3">
          <Button
            variant="primary"
            onClick={() => setIsAddModalOpen(true)}
            disabled={isSaving}
          >
            <PlusIcon className="w-5 h-5 mr-2" />
            Add Criterion
          </Button>

          <Button
            variant="outline"
            onClick={handleAutoBalance}
            disabled={isSaving}
          >
            <ArrowPathIcon className="w-5 h-5 mr-2" />
            Auto-Balance
          </Button>
        </div>

        <div className="flex gap-3">
          {hasChanges && (
            <Button
              variant="secondary"
              onClick={handleReset}
              disabled={isSaving}
            >
              Reset
            </Button>
          )}

          <Button
            variant="primary"
            onClick={handleSave}
            disabled={!isValid || !hasChanges || isSaving}
            isLoading={isSaving}
          >
            Save Changes
          </Button>
        </div>
      </div>

      {/* Drag & drop criteria list */}
      <DragDropContext onDragEnd={handleDragEnd}>
        <Droppable droppableId="criteria-list">
          {(provided, snapshot) => (
            <div
              {...provided.droppableProps}
              ref={provided.innerRef}
              className={`space-y-3 min-h-[200px] ${
                snapshot.isDraggingOver ? 'bg-shazam-50/50 rounded-lg p-2' : ''
              }`}
            >
              <AnimatePresence>
                {criteria.map((criterion, index) => (
                  <CriterionRow
                    key={criterion.name}
                    criterion={criterion}
                    index={index}
                    onWeightChange={(weight) => handleWeightChange(index, weight)}
                    onDelete={() => handleDelete(index)}
                    disabled={isSaving}
                  />
                ))}
              </AnimatePresence>
              {provided.placeholder}
            </div>
          )}
        </Droppable>
      </DragDropContext>

      {/* Empty state */}
      {criteria.length === 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-center py-12 border-2 border-dashed border-gray-300 rounded-lg"
        >
          <PlusIcon className="w-12 h-12 mx-auto text-gray-400 mb-3" />
          <p className="text-gray-600 mb-4">No scoring criteria defined</p>
          <Button variant="primary" onClick={() => setIsAddModalOpen(true)}>
            Add First Criterion
          </Button>
        </motion.div>
      )}

      {/* Add criterion modal */}
      <AddCriterionModal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        onAdd={handleAdd}
        existingNames={criteria.map(c => c.name)}
      />
    </div>
  )
}
