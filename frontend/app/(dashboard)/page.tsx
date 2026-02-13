'use client'

import { motion } from 'framer-motion'
import Link from 'next/link'
import {
  UsersIcon,
  CubeIcon,
  StarIcon,
  ArrowTrendingUpIcon,
  PlusIcon,
  Cog6ToothIcon,
} from '@heroicons/react/24/outline'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { useDashboardMetrics } from '@/hooks/useDashboard'

const containerVariants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.1 },
  },
}

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0 },
}

export default function DashboardPage() {
  const { data: metrics, isLoading } = useDashboardMetrics()

  const stats = [
    {
      name: 'Total Tenants',
      value: metrics?.total_tenants?.toLocaleString() || '--',
      icon: UsersIcon,
      change: metrics?.tenants_growth || '+0%',
      color: 'shazam',
    },
    {
      name: 'Total Products',
      value: metrics?.total_products?.toLocaleString() || '--',
      icon: CubeIcon,
      change: metrics?.products_growth || '+0%',
      color: 'blue',
    },
    {
      name: 'Total Reviews',
      value: metrics?.total_reviews?.toLocaleString() || '--',
      icon: StarIcon,
      change: metrics?.reviews_growth || '+0%',
      color: 'amber',
    },
    {
      name: 'Avg Score',
      value: metrics?.avg_score?.toFixed(2) || '--',
      icon: ArrowTrendingUpIcon,
      change: metrics?.score_growth || '+0%',
      color: 'green',
    },
  ]

  return (
    <div>
      {/* Header */}
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
          <p className="mt-1 text-gray-500">Welcome to the RaaS Platform admin panel</p>
        </div>
        <Link href="/tenants/new">
          <Button variant="primary">
            <PlusIcon className="h-5 w-5 mr-2" />
            New Tenant
          </Button>
        </Link>
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <LoadingSpinner />
        </div>
      )}

      {/* Stats Grid */}
      {!isLoading && (
        <>
          <motion.div
            variants={containerVariants}
            initial="hidden"
            animate="show"
            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8"
          >
            {stats.map((stat) => (
              <motion.div key={stat.name} variants={itemVariants}>
                <Card hover className="relative overflow-hidden">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-500">{stat.name}</p>
                      <p className="mt-1 text-3xl font-bold text-gray-900">{stat.value}</p>
                      <p
                        className={`mt-1 text-sm ${
                          stat.change.startsWith('+') ? 'text-green-600' : 'text-red-600'
                        }`}
                      >
                        {stat.change} from last month
                      </p>
                    </div>
                    <div className="w-12 h-12 bg-gradient-shazam rounded-xl flex items-center justify-center shadow-shazam">
                      <stat.icon className="h-6 w-6 text-white" />
                    </div>
                  </div>
                  {/* Decorative gradient bar */}
                  <div className="absolute bottom-0 left-0 right-0 h-1 bg-gradient-shazam" />
                </Card>
              </motion.div>
            ))}
          </motion.div>

      {/* Stats Grid */}
      <motion.div
        variants={containerVariants}
        initial="hidden"
        animate="show"
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8"
      >
        {stats.map((stat) => (
          <motion.div key={stat.name} variants={itemVariants}>
            <Card hover className="relative overflow-hidden">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-500">{stat.name}</p>
                  <p className="mt-1 text-3xl font-bold text-gray-900">{stat.value}</p>
                  <p className="mt-1 text-sm text-green-600">{stat.change} from last month</p>
                </div>
                <div className="w-12 h-12 bg-gradient-shazam rounded-xl flex items-center justify-center shadow-shazam">
                  <stat.icon className="h-6 w-6 text-white" />
                </div>
              </div>
              {/* Decorative gradient bar */}
              <div className="absolute bottom-0 left-0 right-0 h-1 bg-gradient-shazam" />
            </Card>
          </motion.div>
        ))}
      </motion.div>

          {/* Content Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Recent Activity */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 }}
              className="lg:col-span-2"
            >
              <Card>
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Recent Activity</h2>
                {metrics?.recent_activity && metrics.recent_activity.length > 0 ? (
                  <div className="space-y-4">
                    {metrics.recent_activity.slice(0, 10).map((activity: any, i: number) => (
                      <div
                        key={i}
                        className="flex items-start space-x-4 py-3 border-b border-gray-50 last:border-0"
                      >
                        <div className="w-2 h-2 rounded-full bg-shazam-500 mt-2" />
                        <div className="flex-1">
                          <p className="text-sm text-gray-900">{activity.message}</p>
                          <p className="text-xs text-gray-500 mt-1">
                            {new Date(activity.timestamp).toLocaleString()}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="space-y-4">
                    {[1, 2, 3, 4, 5].map((i) => (
                      <div
                        key={i}
                        className="flex items-center space-x-4 py-3 border-b border-gray-50 last:border-0"
                      >
                        <div className="w-2 h-2 rounded-full bg-gray-300" />
                        <div className="flex-1">
                          <div className="h-4 bg-gray-100 rounded w-3/4" />
                          <div className="h-3 bg-gray-50 rounded w-1/2 mt-2" />
                        </div>
                      </div>
                    ))}
                    <p className="text-center text-sm text-gray-400 mt-4">
                      No recent activity yet
                    </p>
                  </div>
                )}
              </Card>
            </motion.div>

            {/* Quick Actions */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5 }}
            >
              <Card>
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h2>
                <div className="space-y-3">
                  <Link
                    href="/tenants/new"
                    className="flex items-center p-3 rounded-lg bg-shazam-50 text-shazam-700 hover:bg-shazam-100 transition-colors"
                  >
                    <UsersIcon className="h-5 w-5 mr-3" />
                    <span className="text-sm font-medium">Create New Tenant</span>
                  </Link>
                  <Link
                    href="/tenants"
                    className="flex items-center p-3 rounded-lg bg-gray-50 text-gray-700 hover:bg-gray-100 transition-colors"
                  >
                    <CubeIcon className="h-5 w-5 mr-3" />
                    <span className="text-sm font-medium">Manage Tenants</span>
                  </Link>
                  <Link
                    href="/settings"
                    className="flex items-center p-3 rounded-lg bg-gray-50 text-gray-700 hover:bg-gray-100 transition-colors"
                  >
                    <Cog6ToothIcon className="h-5 w-5 mr-3" />
                    <span className="text-sm font-medium">Platform Settings</span>
                  </Link>
                </div>
              </Card>
            </motion.div>
          </div>
        </>
      )}
    </div>
  )
}
