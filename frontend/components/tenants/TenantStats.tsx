'use client'

import { motion } from 'framer-motion'
import {
  CubeIcon,
  ChatBubbleLeftRightIcon,
  ChartBarIcon,
  UsersIcon,
  TrophyIcon,
} from '@heroicons/react/24/outline'
import { Card } from '@/components/ui/Card'
import { TenantStats as TenantStatsType } from '@/lib/types'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'

interface TenantStatsProps {
  stats: TenantStatsType | undefined
  isLoading?: boolean
}

const StatCard = ({
  title,
  value,
  icon: Icon,
  color,
  delay,
}: {
  title: string
  value: string | number
  icon: any
  color: string
  delay: number
}) => (
  <motion.div
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ delay }}
  >
    <Card className="flex items-center space-x-4">
      <div className={`w-12 h-12 ${color} rounded-lg flex items-center justify-center`}>
        <Icon className="w-6 h-6" />
      </div>
      <div>
        <p className="text-sm text-gray-500">{title}</p>
        <p className="text-2xl font-bold text-gray-900">{value}</p>
      </div>
    </Card>
  </motion.div>
)

export const TenantStats = ({ stats, isLoading }: TenantStatsProps) => {
  if (isLoading) {
    return (
      <Card className="flex items-center justify-center py-12">
        <LoadingSpinner />
      </Card>
    )
  }

  if (!stats) {
    return (
      <Card>
        <p className="text-gray-500 text-center py-8">No statistics available</p>
      </Card>
    )
  }

  const statsConfig = [
    {
      title: 'Total Products',
      value: stats.total_products.toLocaleString(),
      icon: CubeIcon,
      color: 'bg-blue-100 text-blue-600',
      delay: 0,
    },
    {
      title: 'Total Reviews',
      value: stats.total_reviews.toLocaleString(),
      icon: ChatBubbleLeftRightIcon,
      color: 'bg-purple-100 text-purple-600',
      delay: 0.1,
    },
    {
      title: 'Total Scores',
      value: stats.total_scores.toLocaleString(),
      icon: ChartBarIcon,
      color: 'bg-amber-100 text-amber-600',
      delay: 0.2,
    },
    {
      title: 'Average Score',
      value: stats.avg_score.toFixed(2),
      icon: TrophyIcon,
      color: 'bg-shazam-100 text-shazam-600',
      delay: 0.3,
    },
    {
      title: 'Active Users',
      value: stats.active_users.toLocaleString(),
      icon: UsersIcon,
      color: 'bg-green-100 text-green-600',
      delay: 0.4,
    },
  ]

  return (
    <div>
      <h2 className="text-lg font-semibold text-gray-900 mb-4">Tenant Statistics</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {statsConfig.map((stat) => (
          <StatCard key={stat.title} {...stat} />
        ))}
      </div>
    </div>
  )
}
