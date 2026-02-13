'use client'

import { motion } from 'framer-motion'
import { Bars3Icon, TrashIcon } from '@heroicons/react/24/outline'
import { Badge } from '@/components/ui/Badge'
import { WeightSlider } from './WeightSlider'
import { ScoringCriterion } from '@/lib/types'
import { Draggable } from '@hello-pangea/dnd'

interface CriterionRowProps {
  criterion: ScoringCriterion
  index: number
  onWeightChange: (weight: number) => void
  onDelete: () => void
  disabled?: boolean
}

export const CriterionRow = ({
  criterion,
  index,
  onWeightChange,
  onDelete,
  disabled,
}: CriterionRowProps) => {
  return (
    <Draggable draggableId={criterion.name} index={index} isDragDisabled={disabled}>
      {(provided, snapshot) => (
        <motion.div
          ref={provided.innerRef}
          {...provided.draggableProps}
          layout
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, x: -20 }}
          className={`bg-white border rounded-lg p-4 ${
            snapshot.isDragging ? 'shadow-shazam-lg border-shazam-300' : 'border-gray-200'
          }`}
        >
          <div className="flex items-start gap-4">
            {/* Drag handle */}
            <div
              {...provided.dragHandleProps}
              className="mt-1 cursor-grab active:cursor-grabbing"
            >
              <Bars3Icon className="w-5 h-5 text-gray-400" />
            </div>

            {/* Content */}
            <div className="flex-1 space-y-3">
              {/* Header */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <h4 className="font-semibold text-gray-900">{criterion.name}</h4>
                  <Badge variant={criterion.type === 'system' ? 'shazam' : 'default'}>
                    {criterion.type}
                  </Badge>
                </div>
                <button
                  onClick={onDelete}
                  disabled={disabled}
                  className="p-1 text-gray-400 hover:text-red-600 transition-colors disabled:opacity-50"
                  title="Delete criterion"
                >
                  <TrashIcon className="w-5 h-5" />
                </button>
              </div>

              {/* Weight slider */}
              <WeightSlider
                value={criterion.weight}
                onChange={onWeightChange}
                disabled={disabled}
              />
            </div>
          </div>
        </motion.div>
      )}
    </Draggable>
  )
}
