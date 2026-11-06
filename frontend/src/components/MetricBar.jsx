import { motion } from 'framer-motion'
import AnimatedNumber from './AnimatedNumber'

/**
 * One score component as a labelled bar plus its number, so the value is
 * readable without relying on colour. Fills from zero on mount (600 ms
 * ease-out) and glides to new values.
 */
export default function MetricBar({ label, value, delay = 0, animated = true, compact = false, muted = false }) {
  const pct = Math.max(0, Math.min(100, Number(value) || 0))
  return (
    <div
      className={compact ? 'min-w-0' : 'min-w-0'}
      role="meter"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={pct}
      aria-valuetext={`${label} ${pct.toFixed(1)} out of 100`}
    >
      <div className="mb-1 flex items-baseline justify-between gap-2">
        <span className={`truncate ${compact ? 'text-2xs' : 'text-xs'} font-medium text-faint`}>{label}</span>
        {animated ? (
          <AnimatedNumber value={pct} delay={delay} className={`${compact ? 'text-xs' : 'text-sm'} font-medium text-ink`} />
        ) : (
          <span className={`tnum ${compact ? 'text-xs' : 'text-sm'} font-medium text-ink`}>{pct.toFixed(1)}</span>
        )}
      </div>
      <div className={`relative ${compact ? 'h-1' : 'h-1.5'} overflow-hidden rounded-full bg-bar-track`}>
        <motion.div
          className={`absolute inset-y-0 left-0 w-full origin-left rounded-full ${muted ? 'bg-faint' : 'bg-bar-fill'}`}
          initial={animated ? { scaleX: 0 } : false}
          animate={{ scaleX: pct / 100 }}
          transition={{ duration: 0.6, ease: 'easeOut', delay }}
          data-testid="metric-fill"
          style={animated ? undefined : { transform: `scaleX(${pct / 100})` }}
        />
      </div>
    </div>
  )
}
