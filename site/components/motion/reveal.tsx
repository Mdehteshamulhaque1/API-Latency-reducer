"use client"

import * as React from "react"
import { motion, useReducedMotion } from "framer-motion"
import type { Variants } from "framer-motion"

import { cn } from "@/lib/utils"

export const EASE = [0.16, 1, 0.3, 1] as const

export const fadeUp: Variants = {
  hidden: { opacity: 0, y: 28 },
  visible: (i: number = 0) => ({
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.7,
      delay: i * 0.09,
      ease: EASE,
    },
  }),
}

interface RevealProps {
  children: React.ReactNode
  className?: string
  delay?: number
  as?: "div" | "section" | "li"
  y?: number
}

/** Scroll-triggered reveal with expo-out easing. Respects reduced motion. */
export function Reveal({ children, className, delay = 0, as = "div", y = 28 }: RevealProps) {
  const reduce = useReducedMotion()
  const Comp = motion[as]
  return (
    <Comp
      className={cn(className)}
      initial={reduce ? false : { opacity: 0, y }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-80px" }}
      transition={{ duration: 0.7, delay, ease: EASE }}
    >
      {children}
    </Comp>
  )
}

/** Stagger container for children that use the `visible` variant above. */
export function Stagger({
  children,
  className,
  amount = 0.2,
}: {
  children: React.ReactNode
  className?: string
  amount?: number
}) {
  const reduce = useReducedMotion()
  return (
    <motion.div
      className={cn(className)}
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, amount }}
      transition={{ staggerChildren: 0.1 }}
    >
      {children}
    </motion.div>
  )
}

export function StaggerItem({
  children,
  className,
  index = 0,
}: {
  children: React.ReactNode
  className?: string
  index?: number
}) {
  return (
    <motion.div className={cn(className)} variants={fadeUp} custom={index}>
      {children}
    </motion.div>
  )
}
