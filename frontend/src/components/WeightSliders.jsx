import { Check, RotateCcw } from 'lucide-react'
import { DEFAULT_WEIGHTS, WEIGHT_KEYS, rebalance, weightTotal } from '../lib/scoring'

const INFO = {
  skills: { label: 'Skills', help: 'Required and preferred skills listed' },
  experience: { label: 'Experience', help: 'Years against the minimum' },
  education: { label: 'Education', help: 'Level against the minimum' },
  semantic: { label: 'Meaning match', help: 'How closely the CV describes this work' },
}

/**
 * Four weight sliders with number boxes and a live total.
 *
 * mode="manual"   each weight moves on its own; the total must reach 100
 *                 (used on the job form, where Run Match waits for 100%).
 * mode="balanced" moving one weight rebalances the others so the total is
 *                 always 100 (used for live "what if" re-ranking).
 */
export default function WeightSliders({ weights, onChange, mode = 'manual', onReset, resetLabel = 'Reset to defaults', idPrefix = 'w', dense = false }) {
  const total = weightTotal(weights)
  const ok = total === 100

  const set = (key, raw) => {
    if (mode === 'balanced') {
      onChange(rebalance(weights, key, raw))
      return
    }
    if (raw === '') {
      onChange({ ...weights, [key]: '' })
      return
    }
    const n = Math.max(0, Math.min(100, Math.round(Number(raw))))
    onChange({ ...weights, [key]: Number.isNaN(n) ? 0 : n })
  }

  return (
    <div>
      <div className={dense ? 'space-y-3' : 'space-y-4'}>
        {WEIGHT_KEYS.map((key) => {
          const v = weights[key]
          const pct = Number(v) || 0
          return (
            <div key={key} className="grid grid-cols-[minmax(0,11rem)_1fr_4.5rem] items-center gap-4">
              <label htmlFor={`${idPrefix}-${key}-range`} className="min-w-0">
                <span className="block text-base font-medium text-ink">{INFO[key].label}</span>
                {!dense && <span className="block text-xs leading-4 text-faint">{INFO[key].help}</span>}
              </label>
              <input
                id={`${idPrefix}-${key}-range`}
                type="range"
                min={0}
                max={100}
                step={1}
                value={pct}
                onChange={(e) => set(key, e.target.value)}
                className="range"
                style={{ '--pct': `${pct}%` }}
                aria-valuetext={`${pct} percent`}
              />
              <div className="relative">
                <input
                  type="number"
                  min={0}
                  max={100}
                  step={1}
                  value={v}
                  onChange={(e) => set(key, e.target.value)}
                  className="input no-spin tnum h-8 pr-6 text-right"
                  aria-label={`${INFO[key].label} weight, percent`}
                />
                <span className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 text-sm text-faint">%</span>
              </div>
            </div>
          )
        })}
      </div>
      <div className="mt-4 flex items-center justify-between gap-3 border-t border-line pt-3">
        <div
          className={`tnum inline-flex items-center gap-1.5 text-sm font-medium ${ok ? 'text-go' : 'text-warn'}`}
          aria-live="polite"
          data-testid="weight-total"
        >
          {ok ? <Check size={14} aria-hidden /> : null}
          <span>Total {total}%</span>
          {!ok && (
            <span className="font-normal text-muted">
              {total < 100 ? `· ${100 - total}% still to assign` : `· ${total - 100}% over`}
            </span>
          )}
        </div>
        {onReset && (
          <button type="button" className="btn-ghost btn-sm" onClick={onReset}>
            <RotateCcw size={13} aria-hidden />
            {resetLabel}
          </button>
        )}
      </div>
    </div>
  )
}

export { DEFAULT_WEIGHTS }
