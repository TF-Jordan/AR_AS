'use client'

import { useState } from 'react'
import { usePathname } from 'next/navigation'
import Link from 'next/link'
import { motion, AnimatePresence } from 'framer-motion'
import {
  HomeIcon,
  UsersIcon,
  ChartBarIcon,
  Cog6ToothIcon,
  ArrowRightOnRectangleIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
} from '@heroicons/react/24/outline'
import { cn } from '@/lib/utils'

const navigation = [
  { name: 'Dashboard', href: '/', icon: HomeIcon },
  { name: 'Tenants', href: '/tenants', icon: UsersIcon },
  { name: 'Analytics', href: '/analytics', icon: ChartBarIcon },
  { name: 'Settings', href: '/settings', icon: Cog6ToothIcon },
]

interface SidebarProps {
  collapsed?: boolean
  onToggle?: () => void
}

export function Sidebar({ collapsed = false, onToggle }: SidebarProps) {
  const pathname = usePathname()

  const isActive = (href: string) => {
    if (href === '/') return pathname === '/'
    return pathname.startsWith(href)
  }

  return (
    <motion.div
      animate={{ width: collapsed ? 72 : 256 }}
      transition={{ duration: 0.2, ease: 'easeInOut' }}
      className="fixed inset-y-0 left-0 z-30 bg-white border-r border-gray-200 flex flex-col"
    >
      {/* Logo */}
      <div className="h-16 flex items-center justify-between px-4 border-b border-gray-200">
        <Link href="/" className="flex items-center space-x-2 overflow-hidden">
          <div className="w-9 h-9 bg-gradient-shazam rounded-lg flex items-center justify-center flex-shrink-0 shadow-shazam">
            <span className="text-white font-bold text-lg">R</span>
          </div>
          <AnimatePresence>
            {!collapsed && (
              <motion.span
                initial={{ opacity: 0, width: 0 }}
                animate={{ opacity: 1, width: 'auto' }}
                exit={{ opacity: 0, width: 0 }}
                className="text-xl font-bold text-gradient-shazam whitespace-nowrap overflow-hidden"
              >
                RaaS Platform
              </motion.span>
            )}
          </AnimatePresence>
        </Link>
        <button
          onClick={onToggle}
          className="p-1 rounded-md text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
        >
          {collapsed ? (
            <ChevronRightIcon className="h-4 w-4" />
          ) : (
            <ChevronLeftIcon className="h-4 w-4" />
          )}
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 mt-4 px-3 space-y-1">
        {navigation.map((item) => {
          const active = isActive(item.href)
          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                'group flex items-center rounded-lg transition-all duration-200 relative',
                collapsed ? 'px-2 py-2 justify-center' : 'px-3 py-2.5',
                active
                  ? 'bg-gradient-shazam text-white shadow-shazam'
                  : 'text-gray-600 hover:bg-shazam-50 hover:text-shazam-600'
              )}
              title={collapsed ? item.name : undefined}
            >
              <item.icon
                className={cn(
                  'flex-shrink-0 h-5 w-5',
                  active ? 'text-white' : 'text-gray-400 group-hover:text-shazam-500'
                )}
              />
              <AnimatePresence>
                {!collapsed && (
                  <motion.span
                    initial={{ opacity: 0, marginLeft: 0 }}
                    animate={{ opacity: 1, marginLeft: 12 }}
                    exit={{ opacity: 0, marginLeft: 0 }}
                    className="text-sm font-medium whitespace-nowrap"
                  >
                    {item.name}
                  </motion.span>
                )}
              </AnimatePresence>
            </Link>
          )
        })}
      </nav>

      {/* User section */}
      <div className="p-3 border-t border-gray-200">
        <div className={cn(
          'flex items-center mb-3',
          collapsed ? 'justify-center' : 'space-x-3'
        )}>
          <div className="w-9 h-9 bg-gradient-shazam rounded-full flex items-center justify-center flex-shrink-0">
            <span className="text-white font-semibold text-sm">A</span>
          </div>
          <AnimatePresence>
            {!collapsed && (
              <motion.div
                initial={{ opacity: 0, width: 0 }}
                animate={{ opacity: 1, width: 'auto' }}
                exit={{ opacity: 0, width: 0 }}
                className="flex-1 min-w-0 overflow-hidden"
              >
                <p className="text-sm font-medium text-gray-900 truncate">Admin</p>
                <p className="text-xs text-gray-500 truncate">admin@raas.local</p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
        <button
          className={cn(
            'w-full flex items-center text-sm text-gray-600 hover:bg-gray-100 rounded-lg transition-colors',
            collapsed ? 'px-2 py-2 justify-center' : 'px-3 py-2'
          )}
          title={collapsed ? 'Logout' : undefined}
        >
          <ArrowRightOnRectangleIcon className="h-5 w-5 flex-shrink-0" />
          <AnimatePresence>
            {!collapsed && (
              <motion.span
                initial={{ opacity: 0, marginLeft: 0 }}
                animate={{ opacity: 1, marginLeft: 8 }}
                exit={{ opacity: 0, marginLeft: 0 }}
                className="whitespace-nowrap"
              >
                Logout
              </motion.span>
            )}
          </AnimatePresence>
        </button>
      </div>
    </motion.div>
  )
}
