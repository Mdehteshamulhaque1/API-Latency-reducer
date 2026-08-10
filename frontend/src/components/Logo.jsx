import { motion } from 'framer-motion'

/**
 * Animated brand logo — gradient bolt mark with a rotating glow ring.
 * size: px for the square mark, showText: renders the wordmark.
 */
export default function Logo({ size = 44, showText = true, light = false, className = '' }) {
  return (
    <span className={`inline-flex items-center gap-3 ${className}`}>
      <span className="relative inline-flex" style={{ width: size, height: size }}>
        {/* rotating gradient conic ring */}
        <motion.span
          className="absolute inset-0 rounded-xl"
          style={{
            background:
              'conic-gradient(from 0deg, #4f46e5, #7c3aed, #06b6d4, #22d3ee, #4f46e5)',
            filter: 'blur(6px)',
            opacity: 0.75,
          }}
          animate={{ rotate: 360 }}
          transition={{ duration: 9, repeat: Infinity, ease: 'linear' }}
        />
        <span className="absolute inset-[3px] rounded-[10px] bg-white" />
        <motion.span
          className="absolute inset-[3px] flex items-center justify-center rounded-[10px]"
          style={{ background: 'linear-gradient(135deg,#4f46e5,#7c3aed 55%,#06b6d4)' }}
          animate={{ scale: [1, 1.05, 1] }}
          transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
        >
          <svg viewBox="0 0 24 24" width={size * 0.55} height={size * 0.55} fill="none">
            <path d="M13.4 3 7 13h4.2l-1.1 8L16.6 11h-4.2l1-8Z" fill="#fff" />
          </svg>
        </motion.span>
      </span>
      {showText && (
        <span className="leading-none">
          <span
            className={`font-display text-xl font-bold tracking-tight ${light ? 'text-white' : 'text-slate-900'}`}
          >
            API<span className="text-gradient">Optimizer</span>
          </span>
          <span
            className={`block text-[10px] font-medium tracking-[0.28em] uppercase mt-1 ${light ? 'text-slate-300' : 'text-slate-400'}`}
          >
            Latency Reducer
          </span>
        </span>
      )}
    </span>
  )
}
