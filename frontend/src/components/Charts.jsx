// Small, dependency-free charts for the dashboard.
// Every chart here is single-series (one hue: the accent), so no legend is
// needed; the panel title names the series. Bars are thin with 4px rounded
// data-ends, gridlines are recessive, values use text colours (never the bar
// colour), each mark has a hover tooltip, and a visually-hidden table carries
// the same numbers for screen readers.
import { useState } from 'react'

function SrTable({ caption, rows, valueLabel }) {
  return (
    <table className="sr-only">
      <caption>{caption}</caption>
      <thead>
        <tr>
          <th scope="col">Item</th>
          <th scope="col">{valueLabel}</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r) => (
          <tr key={r.key}>
            <th scope="row">{r.label}</th>
            <td>{r.value}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

/**
 * Horizontal bars: one row per item, label left, value right.
 * rows: [{ key, label, value, note? }]
 */
export function HBarChart({ rows, caption, valueLabel = 'Count', format = (v) => v.toLocaleString(), onSelect }) {
  const [hover, setHover] = useState(null)
  const max = Math.max(1, ...rows.map((r) => r.value))
  return (
    <figure className="m-0">
      {/* Clickable rows stay in the accessibility tree as buttons; plain rows are
          hidden because the table below carries the same numbers. */}
      <ul className="space-y-1" aria-hidden={onSelect ? undefined : true}>
        {rows.map((r) => {
          const pct = (r.value / max) * 100
          const active = hover === r.key
          const Row = onSelect ? 'button' : 'div'
          return (
            <li key={r.key} className="relative">
              <Row
                type={onSelect ? 'button' : undefined}
                aria-label={onSelect ? `${r.label}: ${format(r.value)}` : undefined}
                onClick={onSelect ? () => onSelect(r) : undefined}
                onFocus={() => setHover(r.key)}
                onBlur={() => setHover(null)}
                onMouseEnter={() => setHover(r.key)}
                onMouseLeave={() => setHover(null)}
                className={`grid w-full grid-cols-[minmax(0,9.5rem)_1fr_3.25rem] items-center gap-3 rounded px-1 py-1.5 text-left ${
                  active ? 'bg-subtle' : ''
                } ${onSelect ? 'cursor-pointer' : ''}`}
              >
                <span className="truncate text-sm text-muted" title={r.label}>
                  {r.label}
                </span>
                <span className="relative h-2 rounded-full bg-bar-track">
                  <span
                    className="absolute inset-y-0 left-0 rounded-full bg-bar-fill transition-[width] duration-500"
                    style={{ width: `${r.value > 0 ? Math.max(pct, 1.5) : 0}%`, opacity: hover && !active ? 0.55 : 1 }}
                  />
                </span>
                <span className="tnum text-right text-sm font-medium text-ink">{format(r.value)}</span>
              </Row>
              {active && r.note && (
                <span
                  role="tooltip"
                  className="pointer-events-none absolute -top-8 left-40 z-10 whitespace-nowrap rounded border border-line bg-surface px-2 py-1 text-xs text-ink shadow-pop"
                >
                  {r.note}
                </span>
              )}
            </li>
          )
        })}
      </ul>
      <SrTable caption={caption} rows={rows} valueLabel={valueLabel} />
    </figure>
  )
}

/**
 * Vertical columns over time. points: [{ key, label, value }]
 * A thin baseline and two recessive gridlines; the hovered column shows its value.
 */
export function ColumnChart({ points, caption, valueLabel = 'Count', height = 150 }) {
  const [hover, setHover] = useState(null)
  const max = Math.max(1, ...points.map((p) => p.value))
  const top = Math.max(1, Math.ceil(max / 2) * 2) // even number so the half-line is whole
  return (
    <figure className="m-0">
      <div className="relative" style={{ height }} aria-hidden>
        {[1, 0.5].map((f) => (
          <div key={f} className="absolute inset-x-0 border-t border-dashed border-line" style={{ top: `${(1 - f) * 100}%` }}>
            <span className="tnum absolute -top-2.5 right-0 bg-surface pl-1 text-2xs text-faint">{Math.round(top * f)}</span>
          </div>
        ))}
        <div className="absolute inset-0 right-6 flex items-end justify-around gap-3 border-b border-line-strong">
          {points.map((p) => {
            const active = hover === p.key
            return (
              <div
                key={p.key}
                className="relative flex h-full w-full max-w-[2.5rem] items-end justify-center"
                onMouseEnter={() => setHover(p.key)}
                onMouseLeave={() => setHover(null)}
              >
                <div
                  className="w-3.5 rounded-t bg-bar-fill transition-[height] duration-500"
                  style={{ height: `${(p.value / top) * 100}%`, minHeight: p.value ? 3 : 0, opacity: hover && !active ? 0.55 : 1 }}
                />
                {active && (
                  <span
                    role="tooltip"
                    className="tnum pointer-events-none absolute z-10 whitespace-nowrap rounded border border-line bg-surface px-2 py-1 text-xs text-ink shadow-pop"
                    style={{ bottom: `calc(${(p.value / top) * 100}% + 6px)` }}
                  >
                    {p.label}: {p.value}
                  </span>
                )}
              </div>
            )
          })}
        </div>
      </div>
      <div className="mr-6 mt-1.5 flex justify-around gap-3" aria-hidden>
        {points.map((p) => (
          <span key={p.key} className="w-full max-w-[2.5rem] text-center text-xs text-faint">
            {p.label}
          </span>
        ))}
      </div>
      <SrTable caption={caption} rows={points} valueLabel={valueLabel} />
    </figure>
  )
}
