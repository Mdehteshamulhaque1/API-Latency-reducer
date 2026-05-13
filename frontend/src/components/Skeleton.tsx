import React from 'react'

interface SkeletonProps {
  className?: string
  count?: number
}

export const Skeleton: React.FC<SkeletonProps> = ({ className = 'h-12 w-full', count = 1 }) => {
  return (
    <div className="space-y-2">
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className={`${className} bg-gray-200 animate-pulse rounded`}
        />
      ))}
    </div>
  )
}
