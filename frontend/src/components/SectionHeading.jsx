import Reveal from './Reveal'

const LIGHT_TONES = {
  brand: 'border-brand-200 bg-brand-50 text-brand-600',
  violet: 'border-violet-200 bg-violet-50 text-violet-600',
  cyan: 'border-cyan-200 bg-cyan-50 text-cyan-600',
  emerald: 'border-emerald-200 bg-emerald-50 text-emerald-600',
  amber: 'border-amber-200 bg-amber-50 text-amber-600',
  rose: 'border-rose-200 bg-rose-50 text-rose-600',
}

const DARK_TONES = {
  brand: 'border-brand-400/30 bg-brand-500/10 text-brand-200',
  violet: 'border-violet-400/30 bg-violet-500/10 text-violet-200',
  cyan: 'border-cyan-400/30 bg-cyan-500/10 text-cyan-200',
  emerald: 'border-emerald-400/30 bg-emerald-500/10 text-emerald-200',
  amber: 'border-amber-400/30 bg-amber-500/10 text-amber-200',
  rose: 'border-rose-400/30 bg-rose-500/10 text-rose-200',
}

export default function SectionHeading({
  eyebrow,
  title,
  description,
  align = 'center',
  light = false,
  tone = 'brand',
  className = '',
}) {
  const alignCls = align === 'center' ? 'text-center mx-auto' : 'text-left'
  return (
    <Reveal className={`max-w-3xl ${alignCls} ${className}`}>
      {eyebrow && (
        <span
          className={`inline-flex items-center gap-2 rounded-full border px-4 py-1.5 text-xs font-semibold tracking-widest uppercase ${
            light ? DARK_TONES[tone] : LIGHT_TONES[tone]
          }`}
        >
          <span className="h-1.5 w-1.5 rounded-full bg-current animate-pulse" />
          {eyebrow}
        </span>
      )}
      <h2
        className={`font-display mt-5 text-3xl font-bold tracking-tight sm:text-4xl lg:text-5xl ${
          light ? 'text-white' : 'text-slate-900'
        }`}
      >
        {title}
      </h2>
      {description && (
        <p
          className={`mt-5 text-base leading-relaxed sm:text-lg ${
            light ? 'text-slate-300' : 'text-slate-500'
          }`}
        >
          {description}
        </p>
      )}
    </Reveal>
  )
}
