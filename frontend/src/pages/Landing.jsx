import { useRef } from 'react'
import { motion, useScroll, useTransform } from 'framer-motion'
import {
  Zap,
  ShieldCheck,
  Gauge,
  BarChart3,
  Cpu,
  Lock,
  ArrowRight,
  Sparkles,
  Database,
  Globe,
  CheckCircle2,
  Quote,
  Activity,
  Timer,
  PieChart,
} from 'lucide-react'
import {
  ResponsiveContainer,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  LineChart,
  Line,
  Legend,
} from 'recharts'
import Navbar from '../components/Navbar'
import Footer from '../components/Footer'
import Button from '../components/Button'
import Reveal from '../components/Reveal'
import SectionHeading from '../components/SectionHeading'
import AnimatedCounter from '../components/AnimatedCounter'
import Blob from '../components/Blob'
import Logo from '../components/Logo'
import Pipeline3D from '../components/Pipeline3D'
import { DOCS_URL } from '../lib/config'

/* ------------------------------------------------------------------ */
/*  Hero                                                               */
/* ------------------------------------------------------------------ */

const HERO_IMAGE =
  'https://images.unsplash.com/photo-1551288049-bebda4e38f71?q=80&w=2200&auto=format&fit=crop'

const heroContainer = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.14, delayChildren: 0.15 } },
}

const heroWord = {
  hidden: { opacity: 0, y: 30, filter: 'blur(6px)' },
  visible: {
    opacity: 1,
    y: 0,
    filter: 'blur(0px)',
    transition: { duration: 0.7, ease: [0.22, 1, 0.36, 1] },
  },
}

function Hero() {
  const ref = useRef(null)
  const { scrollYProgress } = useScroll({ target: ref, offset: ['start start', 'end start'] })
  const bgY = useTransform(scrollYProgress, [0, 1], ['0%', '18%'])
  const fade = useTransform(scrollYProgress, [0, 0.7], [1, 0])

  return (
    <section ref={ref} className="relative overflow-hidden bg-white pt-32 pb-20 sm:pt-40 sm:pb-28">
      {/* Background photo */}
      <motion.div style={{ y: bgY }} className="absolute inset-0 -z-10">
        <img
          src={HERO_IMAGE}
          alt=""
          className="h-[120%] w-full object-cover"
          loading="eager"
        />
        <div className="absolute inset-0 bg-gradient-to-r from-white via-white/92 to-white/70" />
        <div className="absolute inset-0 bg-gradient-to-t from-white via-transparent to-white/40" />
      </motion.div>

      {/* Decorative blobs */}
      <Blob className="-top-20 right-[8%] -z-10" color="violet" size={480} />
      <Blob className="top-40 -left-32 -z-10" color="cyan" size={420} />

      <div className="mx-auto max-w-7xl px-5 sm:px-8">
        <div className="mx-auto max-w-3xl">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="inline-flex items-center gap-2 rounded-full border border-brand-200 bg-white/80 px-4 py-1.5 text-xs font-semibold text-brand-600 shadow-sm backdrop-blur"
          >
            <Sparkles size={14} />
            High-Performance API Optimization Platform
          </motion.div>

          <h1 className="font-display mt-6 text-[clamp(2.2rem,4.8vw,4rem)] font-bold leading-[1.02] tracking-tight text-slate-900">
            <motion.span variants={heroContainer} initial="hidden" animate="visible" className="block">
              <motion.span variants={heroWord} className="inline-block whitespace-nowrap">
                Cut <span className="shimmer-text">latency.</span>{' '}
              </motion.span>
              <motion.span variants={heroWord} className="inline-block whitespace-nowrap">
                Ship <span className="shimmer-text">faster.</span>
              </motion.span>
            </motion.span>
          </h1>

          <motion.p
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.65 }}
            className="mt-6 max-w-xl text-base leading-relaxed text-slate-600 sm:text-lg"
          >
            Redis-backed response caching, intelligent token-bucket rate limiting,
            bulletproof JWT authentication, and real-time analytics — fused into one
            platform that makes your APIs measurably faster.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.8 }}
            className="mt-9 flex flex-wrap items-center gap-4"
          >
            <Button to="/login" size="lg" icon={ArrowRight}>
              Launch the dashboard
            </Button>
            <Button href="#how-it-works" variant="secondary" size="lg" icon={Activity}>
              See how it works
            </Button>
          </motion.div>

          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.8, delay: 1 }}
            className="mt-8 flex items-center gap-2 text-sm text-slate-500"
          >
            <CheckCircle2 size={16} className="text-emerald-500" />
            Free to explore · 2-minute setup · Docker ready
          </motion.div>
        </div>
      </div>
    </section>
  )
}

const heroChartData = [
  { h: '00', ms: 210 }, { h: '02', ms: 188 }, { h: '04', ms: 172 }, { h: '06', ms: 160 },
  { h: '08', ms: 150 }, { h: '10', ms: 138 }, { h: '12', ms: 124 }, { h: '14', ms: 118 },
  { h: '16', ms: 112 }, { h: '18', ms: 108 }, { h: '20', ms: 102 }, { h: '22', ms: 96 },
]

/* ------------------------------------------------------------------ */
/*  Logo marquee                                                       */
/* ------------------------------------------------------------------ */

const brands = ['Nimbus', 'Vantage', 'Orbital', 'Quantica', 'Lumen', 'Nexon', 'Stratos', 'Helios']

function LogoMarquee() {
  return (
    <section className="border-y border-slate-100 bg-slate-50/60 py-10">
      <p className="text-center text-xs font-semibold uppercase tracking-[0.3em] text-slate-400">
        Powering engineering teams at
      </p>
      <div className="mask-fade-x mt-7 overflow-hidden">
        <div className="flex w-max animate-marquee items-center gap-16 pr-16">
          {[...brands, ...brands].map((b, i) => (
            <span
              key={i}
              className="font-display text-xl font-bold text-slate-300 transition-colors hover:text-brand-400"
            >
              {b}
            </span>
          ))}
        </div>
      </div>
    </section>
  )
}

/* ------------------------------------------------------------------ */
/*  Features                                                           */
/* ------------------------------------------------------------------ */

const features = [
  {
    icon: Zap,
    title: 'Redis Response Caching',
    desc: 'Pattern-based cache rules with configurable TTL, per-user scoping, query-param hashing and instant invalidation.',
    gradient: 'from-brand-500 to-violet-500',
  },
  {
    icon: Gauge,
    title: 'Token Bucket Rate Limiter',
    desc: 'Sliding refill rate limiting per user, IP and API key with automatic 429 responses and Retry-After headers.',
    gradient: 'from-accent-500 to-emerald-500',
  },
  {
    icon: Lock,
    title: 'JWT Authentication',
    desc: 'Access and refresh tokens with strict type validation, bcrypt password hashing, and role-based access control.',
    gradient: 'from-rose-500 to-orange-500',
  },
  {
    icon: BarChart3,
    title: 'Real-Time Analytics',
    desc: 'SQL-aggregated dashboards with p95/p99 latency, cache hit ratio, error rates, and endpoint rankings.',
    gradient: 'from-violet-500 to-fuchsia-500',
  },
  {
    icon: Cpu,
    title: 'Performance Monitoring',
    desc: 'Slow-endpoint detection, benchmark reports, and smart optimization suggestions generated from request patterns.',
    gradient: 'from-sky-500 to-cyan-500',
  },
  {
    icon: ShieldCheck,
    title: 'Role-Based Access',
    desc: 'Fine-grained admin / operator / viewer roles that gate cache-rule management and analytics visibility.',
    gradient: 'from-emerald-500 to-teal-500',
  },
]

function Features() {
  return (
    <section id="features" className="relative py-24 sm:py-32">
      <div className="h-px bg-gradient-to-r from-transparent via-brand-400/40 to-transparent" aria-hidden />
      <Blob className="right-0 top-0" color="brand" size={380} />
      <div className="relative mx-auto max-w-7xl px-5 sm:px-8">
        <SectionHeading
          eyebrow="Features"
          title={
            <>
              Everything your API needs to be{' '}
              <span className="text-gradient">fast and secure</span>
            </>
          }
          description="A single middleware stack that handles caching, throttling, auth, and observability — so your backend stays lean and your users stay happy."
        />

        <div className="mt-16 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {features.map((f, i) => (
            <Reveal key={f.title} delay={(i % 3) * 0.12}>
              <motion.article
                whileHover={{ y: -8 }}
                transition={{ type: 'spring', stiffness: 300, damping: 20 }}
                className="card card-hover group relative h-full overflow-hidden p-7"
              >
                <div
                  className={`pointer-events-none absolute -right-10 -top-10 h-32 w-32 rounded-full bg-gradient-to-br ${f.gradient} opacity-10 blur-2xl transition-opacity duration-300 group-hover:opacity-25`}
                />
                <span
                  className={`relative inline-flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br ${f.gradient} text-white shadow-lg transition-transform duration-300 group-hover:scale-110 group-hover:rotate-3`}
                >
                  <f.icon size={22} />
                </span>
                <h3 className="font-display relative mt-5 text-lg font-bold text-slate-900">
                  {f.title}
                </h3>
                <p className="relative mt-3 text-sm leading-relaxed text-slate-500">{f.desc}</p>
              </motion.article>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  )
}

/* ------------------------------------------------------------------ */
/*  How it works — 3D pipeline                                        */
/* ------------------------------------------------------------------ */

function HowItWorks() {
  return (
    <section id="how-it-works" className="relative overflow-hidden bg-slate-950 py-24 sm:py-32">
      <div className="bg-dots absolute inset-0 opacity-[0.12]" aria-hidden />
      <div
        className="absolute inset-0 bg-[radial-gradient(55%_45%_at_55%_25%,rgba(34,211,238,0.14),transparent_70%)]"
        aria-hidden
      />
      <div className="h-px bg-gradient-to-r from-transparent via-cyan-400/40 to-transparent" aria-hidden />
      <Blob className="-top-24 right-1/4" color="cyan" size={420} />

      <div className="relative mx-auto max-w-7xl px-5 sm:px-8">
        <div className="grid items-center gap-14 lg:grid-cols-2">
          <div>
            <SectionHeading
              light
              tone="cyan"
              align="left"
              eyebrow="How it works"
              title={
                <>
                  Watch a request fly through the{' '}
                  <span className="shimmer-text">pipeline in 3D</span>
                </>
              }
              description="Move your cursor over the scene to tilt it. Every request is authenticated, throttled, then cache-checked — hits return instantly, misses pay one database round-trip."
            />
            <div className="mt-8 flex flex-wrap gap-2">
              {['Auth', 'Rate limit', 'Cache', 'Redis', 'MySQL'].map((tag) => (
                <span
                  key={tag}
                  className="rounded-full border border-cyan-400/20 bg-cyan-400/5 px-3.5 py-1.5 text-xs font-medium text-cyan-200/80"
                >
                  {tag}
                </span>
              ))}
            </div>
          </div>
          <Pipeline3D />
        </div>
      </div>
    </section>
  )
}

/* ------------------------------------------------------------------ */
/*  Architecture                                                       */
/* ------------------------------------------------------------------ */

const archLayers = [
  {
    label: 'Clients',
    icon: Globe,
    chips: ['Web apps', 'Mobile', 'IoT', 'Third-party services'],
    gradient: 'from-slate-500 to-slate-700',
  },
  {
    label: 'FastAPI middleware',
    icon: Cpu,
    chips: ['Auth · JWT', 'Token bucket rate limit', 'Correlation ID', 'Response cache', 'Metrics'],
    gradient: 'from-brand-500 to-violet-600',
  },
  {
    label: 'Data layer',
    icon: Database,
    chips: ['Redis — cache & rate-limit state', 'MySQL — analytics & rules', 'Celery — background jobs'],
    gradient: 'from-accent-500 to-cyan-600',
  },
]

function Architecture() {
  return (
    <section id="architecture" className="relative overflow-hidden bg-violet-50/50 py-24 sm:py-32">
      <div className="bg-grid-slate absolute inset-0" aria-hidden />
      <div className="h-px bg-gradient-to-r from-transparent via-violet-400/40 to-transparent" aria-hidden />
      <Blob className="-right-20 top-10" color="violet" size={400} />
      <div className="relative mx-auto max-w-5xl px-5 sm:px-8">
        <SectionHeading
          tone="violet"
          eyebrow="Architecture"
          title={
            <>
              A layered pipeline that stays{' '}
              <span className="text-gradient-violet">fast under load</span>
            </>
          }
          description="Each request flows through a linear, non-blocking chain — anything cached or throttled never touches your database."
        />

        <div className="mt-16 space-y-4">
          {archLayers.map((layer, i) => (
            <Reveal key={layer.label} delay={i * 0.12}>
              <motion.div
                whileHover={{ scale: 1.015 }}
                className="card flex flex-col items-start gap-5 p-6 sm:flex-row sm:items-center"
              >
                <span
                  className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br ${layer.gradient} text-white shadow-lg`}
                >
                  <layer.icon size={22} />
                </span>
                <div className="min-w-0">
                  <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">
                    Layer {i + 1}
                  </p>
                  <h3 className="font-display text-lg font-bold text-slate-900">{layer.label}</h3>
                </div>
                <div className="flex flex-1 flex-wrap justify-start gap-2 sm:justify-end">
                  {layer.chips.map((c) => (
                    <span
                      key={c}
                      className="rounded-full border border-slate-200 bg-white px-3.5 py-1.5 text-xs font-medium text-slate-600 transition-colors hover:border-violet-300 hover:text-violet-600"
                    >
                      {c}
                    </span>
                  ))}
                </div>
              </motion.div>
            </Reveal>
          ))}

          {/* animated arrow connectors */}
          <div className="flex justify-center gap-3 py-1">
            {[0, 1].map((i) => (
              <motion.span
                key={i}
                className="h-8 w-px bg-gradient-to-b from-brand-500 to-accent-500"
                animate={{ scaleY: [0.3, 1, 0.3] }}
                transition={{ duration: 2, repeat: Infinity, delay: i * 0.4 }}
              />
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}

/* ------------------------------------------------------------------ */
/*  Metrics                                                            */
/* ------------------------------------------------------------------ */

const metrics = [
  { label: 'Total requests', value: 128400, suffix: '+', gradient: 'from-brand-500 to-violet-500' },
  { label: 'Average latency', value: 148, suffix: 'ms', prefix: '', gradient: 'from-accent-500 to-cyan-500' },
  { label: 'Cache hit ratio', value: 72.4, suffix: '%', decimals: 1, gradient: 'from-emerald-500 to-teal-500' },
  { label: 'P99 latency', value: 356, suffix: 'ms', gradient: 'from-rose-500 to-orange-500' },
]

function Metrics() {
  return (
    <section id="metrics" className="relative overflow-hidden bg-white py-24 sm:py-32">
      <div className="h-px bg-gradient-to-r from-transparent via-emerald-400/40 to-transparent" aria-hidden />
      <Blob className="-left-24 bottom-0" color="brand" size={420} />
      <div className="relative mx-auto max-w-7xl px-5 sm:px-8">
        <div className="grid items-center gap-14 lg:grid-cols-2">
          <div>
            <SectionHeading
              tone="emerald"
              align="left"
              eyebrow="Metrics"
              title={
                <>
                  Prove the impact,{' '}
                  <span className="text-gradient-emerald">not just the effort</span>
                </>
              }
              description="API Optimizer computes everything with SQL-side aggregations, so dashboards stay instant even with millions of logged requests."
            />
            <div className="mt-10 grid grid-cols-2 gap-5">
              {metrics.map((m, i) => (
                <Reveal key={m.label} delay={i * 0.1}>
                  <div className="card card-hover p-6">
                    <p className="text-xs font-semibold uppercase tracking-widest text-slate-400">
                      {m.label}
                    </p>
                    <p className="font-display mt-3 text-3xl font-bold text-slate-900 sm:text-4xl">
                      <AnimatedCounter
                        value={m.value}
                        decimals={m.decimals ?? 0}
                        suffix={m.suffix}
                        prefix={m.prefix ?? ''}
                      />
                    </p>
                    <span
                      className={`mt-4 block h-1 w-12 rounded-full bg-gradient-to-r ${m.gradient}`}
                    />
                  </div>
                </Reveal>
              ))}
            </div>
          </div>

          <Reveal delay={0.2}>
            <div className="card relative p-6">
              <div className="flex items-center justify-between">
                <h3 className="font-display text-lg font-bold text-slate-900">
                  Latency distribution
                </h3>
                <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-600">
                  <Timer size={13} /> last 24h
                </span>
              </div>
              <div className="mt-6 h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={heroChartData} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" vertical={false} />
                    <XAxis dataKey="h" tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                    <Tooltip
                      contentStyle={{ borderRadius: 12, border: '1px solid #e2e8f0', fontSize: 12 }}
                    />
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                    <Line type="monotone" dataKey="ms" name="Avg (ms)" stroke="#4f46e5" strokeWidth={2.5} dot={false} />
                    <Line
                      type="monotone"
                      data={heroChartData.map((d) => ({ ...d, p95: Math.round(d.ms * 1.7) }))}
                      dataKey="p95"
                      name="P95 (ms)"
                      stroke="#06b6d4"
                      strokeWidth={2}
                      strokeDasharray="6 4"
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          </Reveal>
        </div>
      </div>
    </section>
  )
}

/* ------------------------------------------------------------------ */
/*  Testimonials                                                       */
/* ------------------------------------------------------------------ */

const testimonials = [
  {
    quote:
      'We cut p95 latency by 43% in a single sprint. The cache-rule UI makes optimization feel like configuration, not surgery.',
    name: 'Aarav Mehta',
    role: 'Staff Engineer, Nimbus',
    initials: 'AM',
    gradient: 'from-brand-500 to-violet-500',
  },
  {
    quote:
      'The analytics are the first thing our team checks every morning. Slow-endpoint ranking told us exactly where to focus.',
    name: 'Sofia Reyes',
    role: 'Platform Lead, Orbital',
    initials: 'SR',
    gradient: 'from-accent-500 to-emerald-500',
  },
  {
    quote:
      'Rate limiting with a real token bucket and zero false 429s. Our abuse traffic vanished without touching app code.',
    name: 'Daniel Kim',
    role: 'CTO, Quantica',
    initials: 'DK',
    gradient: 'from-rose-500 to-orange-500',
  },
]

function Testimonials() {
  return (
    <section id="testimonials" className="bg-rose-50/50 py-24 sm:py-32">
      <div className="h-px bg-gradient-to-r from-transparent via-rose-400/40 to-transparent" aria-hidden />
      <div className="mx-auto max-w-7xl px-5 sm:px-8">
        <SectionHeading
          tone="rose"
          eyebrow="Testimonials"
          title={
            <>
              Loved by teams that{' '}
              <span className="text-gradient-rose">ship APIs</span>
            </>
          }
          description="Engineers, platform leads, and CTOs use API Optimizer to keep their backends fast under real traffic."
        />
        <div className="mt-16 grid gap-6 md:grid-cols-3">
          {testimonials.map((t, i) => (
            <Reveal key={t.name} delay={i * 0.12}>
              <motion.figure
                whileHover={{ y: -8 }}
                className="card card-hover relative flex h-full flex-col p-7"
              >
                <Quote size={30} className="text-rose-200" fill="currentColor" />
                <blockquote className="mt-4 flex-1 text-sm leading-relaxed text-slate-600">
                  “{t.quote}”
                </blockquote>
                <figcaption className="mt-6 flex items-center gap-3 border-t border-slate-100 pt-5">
                  <span
                    className={`flex h-11 w-11 items-center justify-center rounded-full bg-gradient-to-br ${t.gradient} text-sm font-bold text-white shadow-md`}
                  >
                    {t.initials}
                  </span>
                  <div>
                    <p className="text-sm font-bold text-slate-900">{t.name}</p>
                    <p className="text-xs text-slate-400">{t.role}</p>
                  </div>
                </figcaption>
              </motion.figure>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  )
}

/* ------------------------------------------------------------------ */
/*  CTA                                                                */
/* ------------------------------------------------------------------ */

function CTA() {
  return (
    <section className="relative overflow-hidden py-24 sm:py-32">
      <div className="absolute inset-0">
        <img
          src="https://images.unsplash.com/photo-1558494949-ef010cbdcc31?q=80&w=2200&auto=format&fit=crop"
          alt=""
          className="h-full w-full object-cover"
          loading="lazy"
        />
        <div className="absolute inset-0 bg-gradient-to-br from-brand-700/95 via-violet-800/95 to-slate-950/95" />
      </div>
      <Blob className="left-[10%] top-0" color="cyan" size={360} />
      <Blob className="right-[8%] bottom-0" color="violet" size={400} />

      <div className="relative mx-auto max-w-3xl px-5 text-center sm:px-8">
        <Reveal>
          <motion.div
            className="mx-auto flex justify-center"
            animate={{ rotate: [0, 6, 0, -6, 0] }}
            transition={{ duration: 8, repeat: Infinity, ease: 'easeInOut' }}
          >
            <Logo size={72} showText={false} />
          </motion.div>
          <h2 className="font-display mt-8 text-3xl font-bold text-white sm:text-5xl">
            Your APIs could be <span className="shimmer-text">2–5× faster</span> today
          </h2>
          <p className="mx-auto mt-5 max-w-xl text-base leading-relaxed text-slate-300">
            Spin up the platform, create a cache rule, and watch the latency chart drop.
            No frontend rewrite. No vendor lock-in.
          </p>
          <div className="mt-10 flex flex-wrap justify-center gap-4">
            <Button to="/login" size="lg" icon={ArrowRight}>
              Get started — it's free
            </Button>
            <Button href={DOCS_URL} variant="secondary" size="lg" icon={PieChart}>
              Browse the API docs
            </Button>
          </div>
          <p className="mt-6 text-xs text-slate-400">
            Docker one-liner included · Works with your existing stack
          </p>
        </Reveal>
      </div>
    </section>
  )
}

/* ------------------------------------------------------------------ */
/*  Page                                                               */
/* ------------------------------------------------------------------ */

export default function Landing() {
  return (
    <div className="min-h-screen bg-white">
      <Navbar />
      <Hero />
      <LogoMarquee />
      <Features />
      <HowItWorks />
      <Architecture />
      <Metrics />
      <Testimonials />
      <CTA />
      <Footer />
    </div>
  )
}
