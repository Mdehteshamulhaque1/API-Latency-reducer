import React from 'react'

interface BadgeProps {
  children: React.ReactNode
  variant?: 'success' | 'error' | 'warning' | 'info' | 'default'
}

export const Badge: React.FC<BadgeProps> = ({ children, variant = 'default' }) => {
  const variantClasses = {
    success: 'bg-emerald-100 text-emerald-800',
    error: 'bg-pink-100 text-pink-800',
    warning: 'bg-amber-100 text-amber-800',
    info: 'bg-sky-100 text-sky-800',
    default: 'bg-slate-100 text-slate-800',
  }

  return (
    <span className={`inline-block px-2 py-1 rounded text-xs font-semibold ${variantClasses[variant]}`}>
      {children}
    </span>
  )
}
