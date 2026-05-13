import React from 'react'

interface CardProps {
  title?: string
  children: React.ReactNode
  className?: string
}

export const Card: React.FC<CardProps> = ({ title, children, className = '' }) => {
  return (
    <div className={`card ${className}`}>
      {title && <h2 className="text-lg font-bold mb-4 text-slate-900">{title}</h2>}
      {children}
    </div>
  )
}
