'use client'

import { useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  CloudArrowUpIcon,
  DocumentArrowUpIcon,
  XMarkIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
} from '@heroicons/react/24/outline'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Modal } from '@/components/ui/Modal'

interface ProductUploaderProps {
  onUpload: (file: File) => void
  isUploading?: boolean
  result?: {
    success: boolean
    total_processed: number
    total_created: number
    total_updated: number
    errors: string[]
  }
}

export const ProductUploader = ({ onUpload, isUploading, result }: ProductUploaderProps) => {
  const [isOpen, setIsOpen] = useState(false)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [isDragging, setIsDragging] = useState(false)

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)

    const files = Array.from(e.dataTransfer.files)
    const csvFile = files.find((file) => file.name.endsWith('.csv'))

    if (csvFile) {
      setSelectedFile(csvFile)
    }
  }, [])

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (files && files[0]) {
      setSelectedFile(files[0])
    }
  }

  const handleUpload = () => {
    if (selectedFile) {
      onUpload(selectedFile)
    }
  }

  const handleClose = () => {
    setIsOpen(false)
    setSelectedFile(null)
  }

  return (
    <>
      <Button variant="primary" onClick={() => setIsOpen(true)}>
        <CloudArrowUpIcon className="h-5 w-5 mr-2" />
        Upload Products
      </Button>

      <Modal
        isOpen={isOpen}
        onClose={handleClose}
        title="Upload Products"
        size="lg"
      >
        <div className="space-y-6">
          {/* Upload area */}
          {!result && (
            <>
              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                className={`relative border-2 border-dashed rounded-lg p-8 transition-all ${
                  isDragging
                    ? 'border-shazam-500 bg-shazam-50'
                    : 'border-gray-300 hover:border-gray-400'
                }`}
              >
                <div className="text-center">
                  <DocumentArrowUpIcon className="mx-auto h-12 w-12 text-gray-400 mb-4" />
                  <p className="text-gray-700 font-medium mb-2">
                    Drop your CSV file here, or click to browse
                  </p>
                  <p className="text-sm text-gray-500 mb-4">
                    CSV files only. Maximum file size: 10MB
                  </p>
                  <input
                    type="file"
                    accept=".csv"
                    onChange={handleFileSelect}
                    className="hidden"
                    id="file-upload"
                    disabled={isUploading}
                  />
                  <label
                    htmlFor="file-upload"
                    className={`inline-flex items-center justify-center font-medium rounded-lg transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 border-2 border-shazam-500 text-shazam-600 hover:bg-shazam-50 focus:ring-shazam-500 px-4 py-2 text-sm cursor-pointer ${
                      isUploading ? 'opacity-50 cursor-not-allowed' : ''
                    }`}
                  >
                    Select File
                  </label>
                </div>
              </div>

              {/* Selected file */}
              <AnimatePresence>
                {selectedFile && (
                  <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                  >
                    <Card className="flex items-center justify-between">
                      <div className="flex items-center space-x-3">
                        <DocumentArrowUpIcon className="h-8 w-8 text-shazam-600" />
                        <div>
                          <p className="font-medium text-gray-900">{selectedFile.name}</p>
                          <p className="text-sm text-gray-500">
                            {(selectedFile.size / 1024).toFixed(2)} KB
                          </p>
                        </div>
                      </div>
                      <button
                        onClick={() => setSelectedFile(null)}
                        disabled={isUploading}
                        className="p-1 text-gray-400 hover:text-red-600 transition-colors disabled:opacity-50"
                      >
                        <XMarkIcon className="h-5 w-5" />
                      </button>
                    </Card>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* CSV format info */}
              <Card variant="bordered" className="p-4 bg-blue-50">
                <h4 className="font-medium text-gray-900 mb-2">CSV Format Requirements</h4>
                <ul className="text-sm text-gray-600 space-y-1 list-disc list-inside">
                  <li>Required columns: <code className="bg-gray-100 px-1 rounded">product_id</code>, <code className="bg-gray-100 px-1 rounded">name</code></li>
                  <li>Optional columns: <code className="bg-gray-100 px-1 rounded">description</code>, <code className="bg-gray-100 px-1 rounded">category</code>, <code className="bg-gray-100 px-1 rounded">sku</code></li>
                  <li>Use comma (,) as delimiter</li>
                  <li>First row should contain column headers</li>
                </ul>
              </Card>
            </>
          )}

          {/* Upload result */}
          {result && (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="space-y-4"
            >
              <div className={`flex items-center gap-3 p-4 rounded-lg ${
                result.success ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'
              }`}>
                {result.success ? (
                  <CheckCircleIcon className="h-6 w-6 flex-shrink-0" />
                ) : (
                  <ExclamationCircleIcon className="h-6 w-6 flex-shrink-0" />
                )}
                <div>
                  <p className="font-semibold">
                    {result.success ? 'Upload Successful!' : 'Upload Completed with Errors'}
                  </p>
                  <p className="text-sm mt-1">
                    Processed: {result.total_processed} | Created: {result.total_created} | Updated: {result.total_updated}
                  </p>
                </div>
              </div>

              {result.errors.length > 0 && (
                <Card className="max-h-60 overflow-y-auto">
                  <h4 className="font-medium text-gray-900 mb-2">Errors</h4>
                  <ul className="text-sm text-red-600 space-y-1">
                    {result.errors.map((error, i) => (
                      <li key={i}>• {error}</li>
                    ))}
                  </ul>
                </Card>
              )}
            </motion.div>
          )}

          {/* Actions */}
          <div className="flex justify-end gap-3 pt-4 border-t">
            <Button variant="secondary" onClick={handleClose} disabled={isUploading}>
              {result ? 'Close' : 'Cancel'}
            </Button>
            {!result && (
              <Button
                variant="primary"
                onClick={handleUpload}
                disabled={!selectedFile || isUploading}
                isLoading={isUploading}
              >
                Upload
              </Button>
            )}
          </div>
        </div>
      </Modal>
    </>
  )
}
