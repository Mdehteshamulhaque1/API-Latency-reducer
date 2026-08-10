import { useEffect, useRef, useState } from 'react'
import { motion, useMotionValue, useSpring } from 'framer-motion'
import { Database, Gauge, Globe, KeyRound, Zap } from 'lucide-react'

/* Nodes laid out on a 100x100 viewBox. z gives real 3D depth. */
const NODES = {
  client: { label: 'Client', sub: 'request', x: 50, y: 12, z: 90, icon: Globe, hue: 'cyan' },
  auth: { label: 'Auth', sub: 'JWT check', x: 24, y: 42, z: 40, icon: KeyRound, hue: 'violet' },
  rate: { label: 'Rate Limit', sub: 'token bucket', x: 50, y: 42, z: 40, icon: Gauge, hue: 'amber' },
  cache: { label: 'Cache', sub: 'redis lookup', x: 76, y: 42, z: 40, icon: Zap, hue: 'cyan' },
  redis: { label: 'Redis', sub: 'store / serve', x: 36, y: 78, z: -60, icon: Database, hue: 'emerald' },
  mysql: { label: 'MySQL', sub: 'rules · analytics', x: 64, y: 78, z: -60, icon: Database, hue: 'rose' },
}

const HIT_PATH = ['client', 'auth', 'rate', 'cache', 'client']
const MISS_PATH = ['client', 'auth', 'rate', 'cache', 'redis', 'mysql', 'cache', 'client']

const CONNECTIONS = [
  ['client', 'auth'],
  ['client', 'rate'],
  ['client', 'cache'],
  ['auth', 'rate'],
  ['rate', 'cache'],
  ['cache', 'redis'],
  ['cache', 'mysql'],
  ['redis', 'mysql'],
]

const HUE = {
  cyan: 'border-cyan-400 bg-cyan-400/15 text-cyan-100 shadow-[0_0_30px_-6px_rgba(34,211,238,0.55)]',
  violet: 'border-violet-400 bg-violet-400/15 text-violet-100 shadow-[0_0_30px_-6px_rgba(167,139,250,0.55)]',
  amber: 'border-amber-400 bg-amber-400/15 text-amber-100 shadow-[0_0_30px_-6px_rgba(251,191,36,0.5)]',
  emerald: 'border-emerald-400 bg-emerald-400/15 text-emerald-100 shadow-[0_0_30px_-6px_rgba(52,211,153,0.5)]',
  rose: 'border-rose-400 bg-rose-400/15 text-rose-100 shadow-[0_0_30px_-6px_rgba(251,113,133,0.5)]',
}

export default function Pipeline3D() {
  const [loop, setLoop] = useState(0) // even = HIT, odd = MISS
  const [step, setStep] = useState(0)
  const [live, setLive] = useState(false)
  const ref = useRef(null)

  const mx = useMotionValue(0)
  const my = useMotionValue(0)
  const rotateX = useSpring(my, { stiffness: 80, damping: 16 })
  const rotateY = useSpring(mx, { stiffness: 80, damping: 16 })

  const isHit = loop % 2 === 0
  const path = isHit ? HIT_PATH : MISS_PATH
  const current = path[step]
  const node = NODES[current]
  const visited = new Set(path.slice(0, step + 1))
  const prev = step > 0 ? path[step - 1] : null
  const next = step < path.length - 1 ? path[step + 1] : null

  useEffect(() => {
    setLive(true)
    const t = setTimeout(() => {
      if (step < path.length - 1) setStep(step + 1)
      else {
        setStep(0)
        setLoop((l) => l + 1)
      }
    }, isHit ? 950 : 820)
    return () => clearTimeout(t)
  }, [step, loop, path.length, isHit])

  useEffect(() => {
    const el = ref.current
    if (!el) return
    const onMove = (e) => {
      const r = el.getBoundingClientRect()
      const px = (e.clientX - r.left) / r.width - 0.5
      const py = (e.clientY - r.top) / r.height - 0.5
      mx.set(px * 26)
      my.set(py * -16)
    }
    el.addEventListener('pointermove', onMove)
    return () => el.removeEventListener('pointermove', onMove)
  }, [mx, my])

  const done = step === path.length - 1
  const status = done
    ? isHit
      ? 'HIT · served from cache'
      : 'MISS · one DB round-trip'
    : `routing → ${NODES[next].label}`
  const latency = done ? (isHit ? '7.5 ms' : '38 ms') : '…'

  return (
    <div className="w-full">
      <div ref={ref} className="[perspective:1600px]">
        <motion.div
          style={{ rotateX, rotateY }}
          className="[transform-style:preserve-3d]"
        >
          <motion.div
            animate={{ rotateY: [0, 9, 0], rotateX: [0, -5, 0] }}
            transition={{ duration: 16, repeat: Infinity, ease: 'easeInOut' }}
            className="relative aspect-[16/10] w-full [transform-style:preserve-3d]"
          >
            {/* soft glow behind the scene */}
            <div
              className="pointer-events-none absolute inset-0 -z-10 rounded-[2rem] bg-[radial-gradient(55%_60%_at_50%_45%,rgba(34,211,238,0.18),transparent_70%)] blur-2xl"
              aria-hidden
            />

            {/* connectors */}
            <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="absolute inset-0 h-full w-full">
              {CONNECTIONS.map(([a, b]) => {
                const A = NODES[a]
                const B = NODES[b]
                const active =
                  prev && ((prev === a && current === b) || (prev === b && current === a))
                return (
                  <line
                    key={`${a}-${b}`}
                    x1={A.x}
                    y1={A.y}
                    x2={B.x}
                    y2={B.y}
                    stroke={active ? '#22d3ee' : 'rgba(148,163,184,0.35)'}
                    strokeWidth={active ? 0.8 : 0.4}
                    strokeDasharray="2 2"
                    strokeLinecap="round"
                    style={active ? { filter: 'drop-shadow(0 0 4px rgba(34,211,238,0.9))' } : undefined}
                  />
                )
              })}
            </svg>

            {/* nodes */}
            {Object.entries(NODES).map(([id, n]) => {
              const reached = visited.has(id)
              return (
                <div
                  key={id}
                  className="absolute"
                  style={{
                    left: `${n.x}%`,
                    top: `${n.y}%`,
                    transform: `translate(-50%, -50%) translateZ(${n.z}px)`,
                  }}
                >
                  <motion.div
                    animate={{
                      opacity: reached ? 1 : 0.85,
                      scale: reached ? 1 : 0.95,
                    }}
                    transition={{ duration: 0.35 }}
                    className={`flex flex-col items-center gap-1 rounded-2xl border bg-slate-800/95 px-4 py-3 backdrop-blur-sm sm:px-5 sm:py-3.5 ${
                      reached ? HUE[n.hue] : 'border-slate-600/60 text-slate-400'
                    }`}
                  >
                    <n.icon size={26} className="sm:hidden" />
                    <n.icon size={30} className="hidden sm:block" />
                    <span className="text-sm font-bold whitespace-nowrap">{n.label}</span>
                    <span className="hidden text-[10px] tracking-wider uppercase opacity-80 sm:block">
                      {n.sub}
                    </span>
                  </motion.div>
                </div>
              )
            })}

            {/* travelling packet */}
            {live && node && (
              <motion.div
                key={`${loop}-${step}`}
                className="absolute z-30"
                style={{ x: '-50%', y: '-50%' }}
                initial={{ opacity: 0, left: `${NODES[path[0]].x}%`, top: `${NODES[path[0]].y}%` }}
                animate={{ left: `${node.x}%`, top: `${node.y}%`, z: node.z, opacity: [0, 1, 1, 0] }}
                transition={{ duration: 0.55, ease: 'easeInOut' }}
              >
                <span className="relative block h-4 w-4 rounded-full bg-white shadow-[0_0_18px_5px_rgba(34,211,238,0.9)]">
                  <motion.span
                    className="absolute inset-0 rounded-full bg-cyan-400"
                    animate={{ scale: [1, 2.2, 1], opacity: [0.7, 0, 0.7] }}
                    transition={{ duration: 1, repeat: Infinity, ease: 'easeOut' }}
                  />
                </span>
              </motion.div>
            )}
          </motion.div>
        </motion.div>
      </div>

      {/* status readout */}
      <div className="mx-auto mt-6 flex max-w-2xl items-center justify-between gap-3 rounded-2xl border border-white/10 bg-slate-800/80 px-5 py-3.5 font-mono text-sm backdrop-blur">
        <span
          className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-bold tracking-widest uppercase ${
            done
              ? isHit
                ? 'bg-cyan-400/15 text-cyan-200'
                : 'bg-rose-400/15 text-rose-200'
              : 'bg-white/5 text-slate-300'
          }`}
        >
          <span className="h-1.5 w-1.5 rounded-full bg-current animate-pulse" />
          {done ? (isHit ? 'hit' : 'miss') : 'live'}
        </span>
        <span className="truncate text-slate-200">{status}</span>
        <span
          className={`text-base font-bold tabular-nums ${
            done ? (isHit ? 'text-cyan-300' : 'text-rose-300') : 'text-slate-400'
          }`}
        >
          {latency}
        </span>
      </div>
    </div>
  )
}
