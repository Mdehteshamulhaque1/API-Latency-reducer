import Reveal from './Reveal'

export default function SectionHeading({ eyebrow, title, description, align = 'center', light = false }) {
  const alignCls = align === 'center' ? 'text-center mx-auto' : 'text-left'
  return (
    <Reveal className={`max-w-3xl ${alignCls}`}>
      {eyebrow && (
        <span
          className={`inline-flex items-center gap-2 rounded-full border px-4 py-1.5 text-xs font-semibold tracking-widest uppercase ${
            light
              ? 'border-white/20 bg-white/10 text-cyan-200'
              : 'border-brand-200 bg-brand-50 text-brand-600'
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
        <p className={`mt-5 text-base leading-relaxed sm:text-lg ${light ? 'text-slate-300' : 'text-slate-500'}`}>
          {description}
        </p>
      )}
    </Reveal>
  )
}
