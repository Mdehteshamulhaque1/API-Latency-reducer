import { motion } from 'framer-motion'

/** Scroll-reveal wrapper using IntersectionObserver via framer-motion. */
export default function Reveal({
  children,
  delay = 0,
  y = 28,
  once = true,
  className = '',
  as = 'div',
}) {
  const Tag = as
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once, amount: 0.2 }}
      transition={{ duration: 0.7, delay, ease: [0.22, 1, 0.36, 1] }}
    >
      <Tag>{children}</Tag>
    </motion.div>
  )
}
