'use client'

import { motion } from 'framer-motion'
import Link from 'next/link'
import { ArrowRightIcon, ShieldCheckIcon, CubeIcon, ChartBarIcon } from '@heroicons/react/24/outline'
import { Button } from '@/components/ui/Button'

const features = [
  {
    icon: ShieldCheckIcon,
    title: 'Multi-Tenant Architecture',
    description: 'Isolated environments for each client with custom scoring configurations.',
  },
  {
    icon: CubeIcon,
    title: 'Product Scoring',
    description: 'AI-powered review aggregation and intelligent scoring engine.',
  },
  {
    icon: ChartBarIcon,
    title: 'Real-Time Analytics',
    description: 'Live dashboards with comprehensive metrics and insights.',
  },
]

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-white">
      {/* Header */}
      <header className="fixed top-0 w-full bg-white/80 backdrop-blur-md border-b border-gray-100 z-50">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <div className="w-8 h-8 bg-gradient-shazam rounded-lg flex items-center justify-center shadow-shazam">
              <span className="text-white font-bold text-lg">R</span>
            </div>
            <span className="text-xl font-bold text-gradient-shazam">RaaS</span>
          </div>
          <Link href="/login">
            <Button variant="outline" size="sm">Sign In</Button>
          </Link>
        </div>
      </header>

      {/* Hero Section */}
      <section className="pt-32 pb-20 px-6">
        <div className="max-w-4xl mx-auto text-center">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <div className="inline-flex items-center px-4 py-1.5 rounded-full bg-shazam-50 text-shazam-700 text-sm font-medium mb-6">
              Review as a Service Platform
            </div>
            <h1 className="text-5xl md:text-6xl font-bold text-gray-900 leading-tight">
              Intelligent Product
              <br />
              <span className="text-gradient-shazam">Scoring Engine</span>
            </h1>
            <p className="mt-6 text-xl text-gray-500 max-w-2xl mx-auto leading-relaxed">
              Multi-tenant platform for aggregating reviews, configuring scoring criteria,
              and delivering actionable product insights at scale.
            </p>
            <div className="mt-10 flex items-center justify-center gap-4">
              <Link href="/tenants">
                <Button size="lg">
                  Get Started
                  <ArrowRightIcon className="ml-2 h-5 w-5" />
                </Button>
              </Link>
              <Link href="/login">
                <Button variant="secondary" size="lg">
                  Admin Login
                </Button>
              </Link>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Features */}
      <section className="py-20 px-6 bg-background-secondary">
        <div className="max-w-6xl mx-auto">
          <motion.div
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            className="grid grid-cols-1 md:grid-cols-3 gap-8"
          >
            {features.map((feature, i) => (
              <motion.div
                key={feature.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.15 }}
                className="bg-white rounded-2xl p-8 shadow-sm border border-gray-100 hover:shadow-shazam transition-all duration-300 hover:-translate-y-1"
              >
                <div className="w-12 h-12 bg-gradient-shazam rounded-xl flex items-center justify-center shadow-shazam mb-5">
                  <feature.icon className="h-6 w-6 text-white" />
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">{feature.title}</h3>
                <p className="text-gray-500 leading-relaxed">{feature.description}</p>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-8 px-6 border-t border-gray-100">
        <div className="max-w-6xl mx-auto flex items-center justify-between text-sm text-gray-500">
          <p>RaaS Platform &copy; {new Date().getFullYear()}</p>
          <p>Built with Next.js & Tailwind CSS</p>
        </div>
      </footer>
    </div>
  )
}
