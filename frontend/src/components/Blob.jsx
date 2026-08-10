import { motion } from 'framer-motion'

/** Soft gradient blob used as a decorative background element. */
export default function Blob({ className = '', color = 'brand', size = 400, style }) {
  const palette = {
    brand: 'radial-gradient(circle at 30% 30%, rgba(99,102,241,0.55), rgba(124,58,237,0.28) 45%, transparent 70%)',
    cyan: 'radial-gradient(circle at 30% 30%, rgba(34,211,238,0.5), rgba(6,182,212,0.22) 45%, transparent 70%)',
    violet: 'radial-gradient(circle at 30% 30%, rgba(167,139,250,0.6), rgba(139,92,246,0.25) 45%, transparent 70%)',
  }
  return (
    <motion.div
      aria-hidden
      className={`pointer-events-none absolute rounded-full ${className}`}
      style={{ width: size, height: size, background: palette[color], ...style }}
      animate={{ scale: [1, 1.12, 1], x: [0, 12, 0], y: [0, -14, 0] }}
      transition={{ duration: 14, repeat: Infinity, ease: 'easeInOut' }}
    />
  )
}
