'use client'

export function Footer() {
  return (
    <footer className="py-6 px-8 border-t border-gray-100 mt-auto">
      <div className="flex items-center justify-between text-sm text-gray-500">
        <p>RaaS Platform &copy; {new Date().getFullYear()}. All rights reserved.</p>
        <div className="flex items-center space-x-4">
          <a href="#" className="hover:text-shazam-600 transition-colors">Documentation</a>
          <a href="#" className="hover:text-shazam-600 transition-colors">Support</a>
          <a href="#" className="hover:text-shazam-600 transition-colors">API Reference</a>
        </div>
      </div>
    </footer>
  )
}
