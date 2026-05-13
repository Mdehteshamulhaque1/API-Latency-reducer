import React from 'react'
import { Loader } from 'lucide-react'

interface LoadingSpinnerProps {
  message?: string
  size?: 'sm' | 'md' | 'lg'
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({ message, size = 'md' }) => {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-8 h-8',
    lg: 'w-12 h-12',
  }

  return (
    <div className="flex flex-col items-center justify-center space-y-3">
      <Loader className={`${sizeClasses[size]} animate-spin text-sky-600`} />
      {message && <p className="text-slate-600">{message}</p>}
    </div>
  )
}
