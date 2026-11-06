import { Github, Heart } from 'lucide-react'
import { DOCS_URL } from '../lib/config'
import Logo from './Logo'

const columns = [
  {
    title: 'Product',
    links: [
      { label: 'Features', href: '#features' },
      { label: 'How it works', href: '#how-it-works' },
      { label: 'Architecture', href: '#architecture' },
      { label: 'Dashboard', href: '/dashboard' },
      { label: 'API docs', href: DOCS_URL },
    ],
  },
  {
    title: 'Resources',
    links: [{ label: 'Contact', href: '#contact' }],
  },
]

export default function Footer() {
  return (
    <footer id="contact" className="relative overflow-hidden border-t border-slate-200 bg-slate-50">
      <div className="bg-dots absolute inset-0 opacity-40" aria-hidden />
      <div className="relative mx-auto max-w-7xl px-5 py-16 sm:px-8">
        <div className="grid gap-12 lg:grid-cols-5">
          <div className="lg:col-span-2">
            <Logo size={40} />
            <p className="mt-5 max-w-sm text-sm leading-relaxed text-slate-500">
              A high-performance API optimization platform — Redis response caching,
              token-bucket rate limiting, JWT authentication, and real-time analytics
              in a single unified system.
            </p>
            <div className="mt-6 flex gap-3">
              <a
                href="https://github.com/Mdehteshamulhaque1/API-Latency-reducer"
                target="_blank"
                rel="noopener noreferrer"
                className="flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-500 transition-all hover:-translate-y-1 hover:border-brand-400 hover:text-brand-600 hover:shadow-md"
                aria-label="GitHub repository"
              >
                <Github size={18} />
              </a>
            </div>
          </div>

          {columns.map((col) => (
            <div key={col.title}>
              <h4 className="text-sm font-semibold uppercase tracking-widest text-slate-900">
                {col.title}
              </h4>
              <ul className="mt-5 space-y-3">
                {col.links.map((l) => (
                  <li key={l.label}>
                    <a
                      href={l.href}
                      className="group inline-flex items-center gap-1.5 text-sm text-slate-500 transition-colors hover:text-brand-600"
                    >
                      <span className="h-px w-0 bg-brand-500 transition-all duration-300 group-hover:w-3" />
                      {l.label}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-14 flex flex-col items-center justify-between gap-4 border-t border-slate-200 pt-8 sm:flex-row">
          <p className="text-xs text-slate-400">
            © {new Date().getFullYear()} API Optimizer. All rights reserved.
          </p>
          <p className="inline-flex items-center gap-1.5 text-xs text-slate-400">
            Built with <Heart size={14} className="text-rose-500" fill="currentColor" /> FastAPI · Redis · React
          </p>
        </div>
      </div>
    </footer>
  )
}
