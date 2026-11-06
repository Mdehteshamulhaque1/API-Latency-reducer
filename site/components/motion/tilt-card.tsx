"use client"

import * as React from "react"
import {
  motion,
  useMotionValue,
  useSpring,
  useTransform,
  useReducedMotion,
  type HTMLMotionProps,
} from "framer-motion"

import { cn } from "@/lib/utils"

interface TiltCardProps extends HTMLMotionProps<"div"> {
  max?: number
  children: React.ReactNode
}

/** Subtle 3D tilt on hover (max ~5deg), with spring smoothing. */
export function TiltCard({ children, className, max = 5, ...props }: TiltCardProps) {
  const reduce = useReducedMotion()
  const px = useMotionValue(0.5)
  const py = useMotionValue(0.5)

  const rotateX = useSpring(useTransform(py, [0, 1], [max, -max]), {
    stiffness: 220,
    damping: 24,
  })
  const rotateY = useSpring(useTransform(px, [0, 1], [-max, max]), {
    stiffness: 220,
    damping: 24,
  })

  function onPointerMove(e: React.PointerEvent<HTMLDivElement>) {
    if (reduce) return
    const rect = e.currentTarget.getBoundingClientRect()
    px.set((e.clientX - rect.left) / rect.width)
    py.set((e.clientY - rect.top) / rect.height)
  }

  function onPointerLeave() {
    px.set(0.5)
    py.set(0.5)
  }

  return (
    <div className="tilt-perspective">
      <motion.div
        className={cn(className)}
        style={reduce ? undefined : { rotateX, rotateY, transformStyle: "preserve-3d" }}
        onPointerMove={onPointerMove}
        onPointerLeave={onPointerLeave}
        whileHover={{ y: -4 }}
        transition={{ type: "spring", stiffness: 300, damping: 24 }}
        {...props}
      >
        {children}
      </motion.div>
    </div>
  )
}
