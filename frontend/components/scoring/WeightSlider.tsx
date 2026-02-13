'use client'

import { motion } from 'framer-motion'
import { useState } from 'react'

interface WeightSliderProps {
  value: number
  onChange: (value: number) => void
  disabled?: boolean
}

export const WeightSlider = ({ value, onChange, disabled }: WeightSliderProps) => {
  const [isDragging, setIsDragging] = useState(false)
  const percentage = Math.round(value * 100)

  return (
    <div className="relative">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-gray-700">Weight</span>
        <motion.span
          className="text-sm font-bold text-shazam-600"
          animate={{ scale: isDragging ? 1.1 : 1 }}
        >
          {percentage}%
        </motion.span>
      </div>

      <div className="relative h-2 bg-gray-200 rounded-full overflow-hidden">
        {/* Gradient track */}
        <motion.div
          className="absolute inset-y-0 left-0 bg-gradient-shazam rounded-full"
          style={{ width: `${percentage}%` }}
          animate={{ opacity: isDragging ? 1 : 0.9 }}
        />

        {/* Input slider */}
        <input
          type="range"
          min="0"
          max="100"
          value={percentage}
          onChange={(e) => onChange(parseInt(e.target.value) / 100)}
          onMouseDown={() => setIsDragging(true)}
          onMouseUp={() => setIsDragging(false)}
          onTouchStart={() => setIsDragging(true)}
          onTouchEnd={() => setIsDragging(false)}
          disabled={disabled}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer disabled:cursor-not-allowed"
        />

        {/* Custom thumb */}
        <motion.div
          className="absolute top-1/2 -translate-y-1/2 w-4 h-4 bg-white rounded-full shadow-shazam pointer-events-none"
          style={{ left: `calc(${percentage}% - 8px)` }}
          animate={{
            scale: isDragging ? 1.2 : 1,
            boxShadow: isDragging
              ? '0 4px 12px rgba(0, 136, 255, 0.4)'
              : '0 2px 8px rgba(0, 136, 255, 0.2)',
          }}
          transition={{ type: 'spring', stiffness: 300, damping: 20 }}
        />
      </div>
    </div>
  )
}
