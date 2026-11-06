import { motion } from 'framer-motion'
import { METRICS } from '../lib/scoring'

// Series are told apart by line style as well as colour (colour-blind safe).
export const SERIES_STYLES = [
  { stroke: 'rgb(var(--accent))', fill: 'rgb(var(--accent) / 0.14)', dash: undefined },
  { stroke: 'rgb(var(--ink) / 0.75)', fill: 'rgb(var(--ink) / 0.06)', dash: '5 3' },
  { stroke: 'rgb(var(--warn))', fill: 'rgb(var(--warn) / 0.08)', dash: '1.5 3' },
]

/** Four-axis radar of the score components (0-100). */
export default function RadarChart({ series, size = 220 }) {
  const c = size / 2
  const r = size / 2 - 40
  // Axes: Skills (top), Experience (right), Education (bottom), Meaning (left)
  const angle = (i) => -Math.PI / 2 + (i * Math.PI * 2) / METRICS.length
  const pt = (i, v) => [c + Math.cos(angle(i)) * r * (v / 100), c + Math.sin(angle(i)) * r * (v / 100)]
  const poly = (vals) =>
    METRICS.map((m, i) => pt(i, vals[m.field] ?? 0))
      .map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`)
      .join(' ')

  return (
    <svg
      viewBox={`0 0 ${size} ${size}`}
      width="100%"
      style={{ maxWidth: size }}
      role="img"
      aria-label={`Radar chart of score components for ${series.map((s) => s.label).join(', ')}`}
    >
      {[25, 50, 75, 100].map((ring) => (
        <polygon
          key={ring}
          points={METRICS.map((_, i) => pt(i, ring).join(',')).join(' ')}
          fill="none"
          stroke="rgb(var(--line))"
          strokeWidth={ring === 100 ? 1.25 : 1}
        />
      ))}
      {METRICS.map((m, i) => {
        const [x, y] = pt(i, 100)
        // Labels sit just beyond each axis tip, centred so nothing clips.
        const side = Math.abs(x - c) > 2
        const lx = side ? x + (x > c ? -2 : 2) : x
        const ly = side ? y + 16 : y + (y < c ? -12 : 13)
        return (
          <g key={m.key}>
            <line x1={c} y1={c} x2={x} y2={y} stroke="rgb(var(--line))" />
            <text
              x={lx}
              y={ly}
              textAnchor="middle"
              dominantBaseline="middle"
              className="fill-[rgb(var(--faint))] text-[10px] font-medium"
            >
              {m.label}
            </text>
          </g>
        )
      })}
      {series.map((s, idx) => {
        const st = SERIES_STYLES[idx % SERIES_STYLES.length]
        return (
          <motion.polygon
            key={s.label + idx}
            points={poly(s.values)}
            fill={st.fill}
            stroke={st.stroke}
            strokeWidth={1.75}
            strokeDasharray={st.dash}
            strokeLinejoin="round"
            initial={{ opacity: 0, scale: 0.6 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5, ease: 'easeOut', delay: 0.1 + idx * 0.08 }}
            style={{ transformOrigin: `${c}px ${c}px` }}
          />
        )
      })}
    </svg>
  )
}
