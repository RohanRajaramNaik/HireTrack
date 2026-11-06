import { motion } from 'framer-motion'
import AnimatedNumber from './AnimatedNumber'

/**
 * One score component as a bar plus its number, so the value is readable
 * without relying on colour. Fills from zero on mount (600 ms ease-out) and
 * glides to new values.
 *
 * layout="stacked": label and number above the bar (panels)
 * layout="inline":  bar with the number to its right, label for screen readers only (result rows)
 */
export default function MetricBar({ label, value, delay = 0, animated = true, layout = 'stacked', hideLabel = false }) {
  const pct = Math.max(0, Math.min(100, Number(value) || 0))
  const inline = layout === 'inline' || hideLabel
  const number = animated ? (
    <AnimatedNumber value={pct} delay={delay} className="text-sm font-medium text-ink" />
  ) : (
    <span className="tnum text-sm font-medium text-ink">{pct.toFixed(1)}</span>
  )
  const bar = (
    <div className={`relative ${inline ? 'h-1.5 flex-1' : 'h-1.5'} overflow-hidden rounded-full bg-bar-track`}>
      <motion.div
        className="absolute inset-y-0 left-0 w-full origin-left rounded-full bg-bar-fill"
        initial={animated ? { scaleX: 0 } : false}
        animate={{ scaleX: pct / 100 }}
        transition={{ duration: 0.6, ease: 'easeOut', delay }}
        data-testid="metric-fill"
        style={animated ? undefined : { transform: `scaleX(${pct / 100})` }}
      />
    </div>
  )
  return (
    <div
      className="min-w-0"
      role="meter"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={pct}
      aria-valuetext={`${label} ${pct.toFixed(1)} out of 100`}
    >
      {inline ? (
        <div className="flex items-center gap-2.5">
          <span className="sr-only">{label}</span>
          {bar}
          <span className="w-9 shrink-0 text-right">{number}</span>
        </div>
      ) : (
        <>
          <div className="mb-1 flex items-baseline justify-between gap-2">
            <span className="truncate text-xs font-medium text-faint">{label}</span>
            {number}
          </div>
          {bar}
        </>
      )}
    </div>
  )
}
