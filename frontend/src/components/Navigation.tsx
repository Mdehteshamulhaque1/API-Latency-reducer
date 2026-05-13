import React from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/store'
import { LogOut, BarChart3, Settings, Shield } from 'lucide-react'

export const Navigation: React.FC = () => {
  const navigate = useNavigate()
  const { logout, user } = useAuthStore()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <nav className="glass-panel sticky top-0 z-30 border-x-0 border-t-0 rounded-none">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <Link to="/dashboard" className="flex items-center space-x-2">
            <span className="flex h-10 w-10 items-center justify-center rounded-2xl bg-gradient-to-br from-[rgb(10,102,194)] via-sky-500 to-pink-500 shadow-lg shadow-sky-500/25">
              <Shield className="w-5 h-5 text-white" />
            </span>
            <span className="text-xl font-extrabold tracking-tight text-slate-900">API Optimizer</span>
          </Link>

          <div className="flex items-center space-x-8">
            <Link to="/dashboard" className="flex items-center space-x-1 text-slate-600 hover:text-[rgb(10,102,194)] transition-colors">
              <BarChart3 className="w-5 h-5" />
              <span>Dashboard</span>
            </Link>
            <Link to="/rules" className="flex items-center space-x-1 text-slate-600 hover:text-pink-600 transition-colors">
              <Settings className="w-5 h-5" />
              <span>Cache Rules</span>
            </Link>

            <div className="flex items-center space-x-4 pl-8 border-l border-sky-100">
              <span className="rounded-full bg-sky-50 px-3 py-1 text-sm font-semibold text-slate-700 ring-1 ring-sky-100">{user?.username}</span>
              <button
                onClick={handleLogout}
                className="flex items-center space-x-1 rounded-full px-3 py-2 text-pink-600 hover:bg-pink-50 hover:text-pink-700 transition-colors"
              >
                <LogOut className="w-5 h-5" />
                <span>Logout</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </nav>
  )
}
