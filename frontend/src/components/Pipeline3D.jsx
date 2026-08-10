import { useEffect, useRef, useState } from 'react'
import { motion, useMotionValue, useSpring } from 'framer-motion'
import { Database, Gauge, Globe, KeyRound, Zap } from 'lucide-react'

/* Nodes laid out on a 100x100 viewBox. z gives real 3D depth. */
const NODES = {
  client: { label: 'Client', sub: 'request', x: 50, y: 10, z: 70, icon: Globe, hue: 'cyan' },
  auth: { label: 'Auth', sub: 'JWT check', x: 25, y: 42, z: 25, icon: KeyRound, hue: 'violet' },
  rate: { label: 'Rate Limit', sub: 'token bucket', x: 50, y: 42, z: 25, icon: Gauge, hue: 'amber' },
  cache: { label: 'Cache', sub: 'redis lookup', x: 75, y: 42, z: 25, icon: Zap, hue: 'cyan' },
  redis: { label: 'Redis', sub: 'store / serve', x: 38, y: 78, z: -45, icon: Database, hue: 'emerald' },
  mysql: { label: 'MySQL', sub: 'rules · analytics', x: 62, y: 78, z: -45, icon: Database, hue: 'rose' },
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
  cyan: { node: 'border-cyan-400/60 bg-cyan-400/10 text-cyan-200', dot: 'bg-cyan-400' },
  violet: { node: 'border-violet-400/60 bg-violet-400/10 text-violet-200', dot: 'bg-violet-400' },
  amber: { node: 'border-amber-400/60 bg-amber-400/10 text-amber-200', dot: 'bg-amber-400' },
  emerald: { node: 'border-emerald-400/60 bg-emerald-400/10 text-emerald-200', dot: 'bg-emerald-400' },
  rose: { node: 'border-rose-400/60 bg-rose-400/10 text-rose-200', dot: 'bg-rose-400' },
}

export default function Pipeline3D() {
  const [loop, setLoop] = useState(0) // even = HIT, odd = MISS
  const [step, setStep] = useState(0)
  const [live, setLive] = useState(false)
  const ref = useRef(null)

  const mx = useMotionValue(0)
  const my = useMotionValue(0)
  const rotateX = useSpring(my, { stiffness: 90, damping: 18 })
  const rotateY = useSpring(mx, { stiffness: 90, damping: 18 })

  const isHit = loop % 2 === 0
  const path = isHit ? HIT_PATH : MISS_PATH
  const current = path[step]
  const node = NODES[current]
  const visited = new Set(path.slice(0, step + 1))
  const prev = step > 0 ? path[step - 1] : null

  useEffect(() => {
    setLive(true)
    const t = setTimeout(() => {
      if (step < path.length - 1) setStep(step + 1)
      else {
        setStep(0)
        setLoop((l) => l + 1)
      }
    }, isHit ? 900 : 780)
    return () => clearTimeout(t)
  }, [step, loop, path.length, isHit])

  useEffect(() => {
    const el = ref.current
    if (!el) return
    const onMove = (e) => {
      const r = el.getBoundingClientRect()
      const px = (e.clientX - r.left) / r.width - 0.5
      const py = (e.clientY - r.top) / r.height - 0.5
      mx.set(px * 22)
      my.set(py * -14)
    }
    el.addEventListener('pointermove', onMove)
    return () => el.removeEventListener('pointermove', onMove)
  }, [mx, my])

  const done = step === path.length - 1
  const status = done
    ? isHit
      ? 'HIT · served from cache'
      : 'MISS · one DB round-trip'
    : `routing → ${NODES[path[step + 1] ?? current].label}`
  const latency = done ? (isHit ? '7.5 ms' : '38 ms') : '…'

  return (
    <div className="w-full">
      <div ref={ref} className="[perspective:1400px]">
        <motion.div
          style={{ rotateX, rotateY }}
          className="relative mx-auto aspect-[4/5] w-full max-w-md [transform-style:preserve-3d]"
        >
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
                  stroke={active ? 'rgba(34,211,238,0.9)' : 'rgba(148,163,184,0.22)'}
                  strokeWidth={active ? 0.5 : 0.3}
                  strokeDasharray="2.5 2.5"
                  strokeLinecap="round"
                />
              )
            })}
          </svg>

          {/* nodes */}
          {Object.entries(NODES).map(([id, n]) => {
            const reached = visited.has(id)
            const hue = HUE[n.hue]
            return (
              <div
                key={id}
                className="absolute -translate-x-1/2 -translate-y-1/2"
                style={{ left: `${n.x}%`, top: `${n.y}%`, transform: `translate(-50%, -50%) translateZ(${n.z}px)` }}
              >
                <motion.div
                  animate={{ opacity: reached ? 1 : 0.5, scale: reached ? 1 : 0.94 }}
                  transition={{ duration: 0.35 }}
                  className={`flex flex-col items-center gap-1.5 rounded-2xl border bg-white/[0.04] px-3 py-2.5 backdrop-blur-sm transition-colors sm:px-4 ${
                    reached ? hue.node : 'border-white/10 text-slate-400'
                  }`}
                >
                  <n.icon size={20} />
                  <span className="text-[11px] font-bold whitespace-nowrap">{n.label}</span>
                  <span className="hidden text-[9px] tracking-wider uppercase opacity-70 sm:block">
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
              animate={{
                left: `${node.x}%`,
                top: `${node.y}%`,
                z: node.z,
                opacity: [0, 1, 1, 0],
              }}
              transition={{ duration: 0.55, ease: 'easeInOut' }}
            >
              <span className="block h-3 w-3 rounded-full bg-cyan-300 shadow-[0_0_22px_5px_rgba(34,211,238,0.65)]" />
            </motion.div>
          )}
        </motion.div>
      </div>

      {/* status readout */}
      <div className="mx-auto mt-6 flex max-w-md items-center justify-between gap-3 rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3 font-mono text-xs backdrop-blur">
        <span
          className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[10px] font-bold tracking-widest uppercase ${
            done ? (isHit ? 'bg-cyan-400/15 text-cyan-200' : 'bg-rose-400/15 text-rose-200') : 'bg-white/5 text-slate-300'
          }`}
        >
          <span className="h-1.5 w-1.5 rounded-full bg-current animate-pulse" />
          {done ? (isHit ? 'hit' : 'miss') : 'live'}
        </span>
        <span className="truncate text-slate-300">{status}</span>
        <span className={`font-bold tabular-nums ${done ? (isHit ? 'text-cyan-300' : 'text-rose-300') : 'text-slate-400'}`}>
          {latency}
        </span>
      </div>
    </div>
  )
}
