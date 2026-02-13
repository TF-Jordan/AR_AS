'use client'

import { motion } from 'framer-motion'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'

export default function SettingsPage() {
  return (
    <div className="max-w-3xl">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Settings</h1>
        <p className="text-gray-500 mb-8">Platform configuration and preferences</p>

        <div className="space-y-6">
          <Card>
            <h2 className="text-lg font-semibold text-gray-900 mb-4">API Configuration</h2>
            <div className="space-y-4">
              <Input
                label="API Base URL"
                defaultValue="http://localhost:8000/api/v1"
                helperText="Backend API endpoint"
              />
              <Input
                label="Keycloak Issuer"
                defaultValue="http://localhost:8080/realms/raas"
                helperText="Keycloak realm URL for authentication"
              />
            </div>
          </Card>

          <Card>
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Platform Settings</h2>
            <p className="text-sm text-gray-500 mb-4">
              Additional platform settings will be available in future updates.
            </p>
            <Button variant="secondary" disabled>Save Changes</Button>
          </Card>
        </div>
      </motion.div>
    </div>
  )
}
