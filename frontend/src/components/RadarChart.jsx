import { motion } from 'framer-motion'
import { METRICS } from '../lib/scoring'

// Series are told apart by line style as well as colour (colour-blind safe).
export const SERIES_STYLES = [
  { stroke: 'rgb(var(--accent))', fill: 'rgb(var(--accent) / 0.14)', dash: undefined },
  { stroke: 'rgb(var(--ink) / 0.75)', fill: 'rgb(var(--ink) / 0.06)', dash: '5 3' },
  { stroke: 'rgb(var(--warn))', fill: 'rgb(var(--warn) / 0.08)', dash: '1.5 3' },
]

const SIDE_GUTTER = 62 // room for "Experience" / "Meaning" labels beside the chart

/** Four-axis radar of the score components (0-100). */
export default function RadarChart({ series, size = 220 }) {
  const width = size + SIDE_GUTTER * 2
  const cx = width / 2
  const cy = size / 2
  const r = size / 2 - 22
  // Axes clockwise from the top: Skills, Experience, Education, Meaning
  const angle = (i) => -Math.PI / 2 + (i * Math.PI * 2) / METRICS.length
  const pt = (i, v) => [cx + Math.cos(angle(i)) * r * (v / 100), cy + Math.sin(angle(i)) * r * (v / 100)]
  const poly = (vals) =>
    METRICS.map((m, i) => pt(i, vals[m.field] ?? 0))
      .map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`)
      .join(' ')

  const labelPos = (i) => {
    const [x, y] = pt(i, 100)
    if (i === 0) return { x, y: y - 10, anchor: 'middle' }
    if (i === 2) return { x, y: y + 12, anchor: 'middle' }
    return i === 1 ? { x: x + 8, y, anchor: 'start' } : { x: x - 8, y, anchor: 'end' }
  }

  return (
    <svg
      viewBox={`0 0 ${width} ${size}`}
      width="100%"
      style={{ maxWidth: width }}
      role="img"
      aria-label={`Radar chart of the four score parts for ${series.map((s) => s.label).join(', ')}`}
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
        const l = labelPos(i)
        return (
          <g key={m.key}>
            <line x1={cx} y1={cy} x2={x} y2={y} stroke="rgb(var(--line))" />
            <text x={l.x} y={l.y} textAnchor={l.anchor} dominantBaseline="middle" fill="rgb(var(--faint))" fontSize="11" fontWeight="500">
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
            animate={{ opacity: 1, scale: 1, points: poly(s.values) }}
            transition={{ duration: 0.5, ease: 'easeOut', delay: 0.1 + idx * 0.08 }}
            style={{ transformOrigin: `${cx}px ${cy}px` }}
          />
        )
      })}
    </svg>
  )
}
