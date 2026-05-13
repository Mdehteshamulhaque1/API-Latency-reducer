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
    <nav className="bg-white shadow-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <Link to="/dashboard" className="flex items-center space-x-2">
            <Shield className="w-8 h-8 text-blue-600" />
            <span className="text-xl font-bold text-gray-800">API Optimizer</span>
          </Link>

          <div className="flex items-center space-x-8">
            <Link to="/dashboard" className="flex items-center space-x-1 text-gray-700 hover:text-blue-600">
              <BarChart3 className="w-5 h-5" />
              <span>Dashboard</span>
            </Link>
            <Link to="/rules" className="flex items-center space-x-1 text-gray-700 hover:text-blue-600">
              <Settings className="w-5 h-5" />
              <span>Cache Rules</span>
            </Link>

            <div className="flex items-center space-x-4 pl-8 border-l">
              <span className="text-gray-700">{user?.username}</span>
              <button
                onClick={handleLogout}
                className="flex items-center space-x-1 text-red-600 hover:text-red-700"
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
