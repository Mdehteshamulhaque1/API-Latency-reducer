import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'

const styles = {
  primary:
    'bg-gradient-to-r from-brand-600 via-violet-600 to-accent-500 text-white shadow-lg shadow-brand-600/25 hover:shadow-xl hover:shadow-brand-600/30 hover:brightness-110',
  secondary:
    'bg-white text-slate-800 border border-slate-200 hover:border-brand-400 hover:text-brand-600 shadow-sm hover:shadow-md',
  ghost:
    'text-slate-600 hover:text-brand-600 hover:bg-brand-50',
  danger: 'bg-rose-600 text-white hover:bg-rose-700 shadow-lg shadow-rose-600/25',
}

const sizes = {
  sm: 'px-4 py-2 text-sm',
  md: 'px-6 py-3 text-sm',
  lg: 'px-8 py-4 text-base',
}

function ButtonInner({ variant, size, icon: Icon, children }) {
  return (
    <>
      <span className="relative z-10 flex items-center justify-center gap-2">
        {Icon && <Icon size={18} className={size === 'lg' ? 'w-5 h-5' : 'w-4 h-4'} />}
        {children}
      </span>
      <span
        aria-hidden
        className="absolute inset-0 -z-0 rounded-xl opacity-0 transition-opacity duration-300 group-hover:opacity-100"
        style={{
          background:
            'radial-gradient(120px 60px at 50% 120%, rgba(255,255,255,0.35), transparent)',
        }}
      />
    </>
  )
}

export default function Button({
  to,
  href,
  onClick,
  variant = 'primary',
  size = 'md',
  icon,
  children,
  className = '',
  type = 'button',
  disabled,
}) {
  const base = `group relative inline-flex items-center justify-center overflow-hidden rounded-xl font-semibold transition-all duration-300 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2 disabled:opacity-60 disabled:cursor-not-allowed ${styles[variant]} ${sizes[size]} ${className}`

  if (to) {
    return (
      <motion.span whileTap={{ scale: 0.97 }}>
        <Link to={to} onClick={onClick} className={base}>
          <ButtonInner variant={variant} size={size} icon={icon}>
            {children}
          </ButtonInner>
        </Link>
      </motion.span>
    )
  }

  if (href) {
    const isAnchor = href.startsWith('#')
    return (
      <motion.a
        whileTap={{ scale: 0.97 }}
        href={href}
        onClick={onClick}
        {...(isAnchor ? {} : { target: '_blank', rel: 'noreferrer' })}
        className={base}
      >
        <ButtonInner variant={variant} size={size} icon={icon}>
          {children}
        </ButtonInner>
      </motion.a>
    )
  }

  return (
    <motion.button
      whileTap={{ scale: 0.97 }}
      whileHover={{ y: -2 }}
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={base}
    >
      <ButtonInner variant={variant} size={size} icon={icon}>
        {children}
      </ButtonInner>
    </motion.button>
  )
}
