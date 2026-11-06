import { AlertCircle } from 'lucide-react'
import { useId } from 'react'

/** Label + control + hint/counter + inline error. Children receive {id, describedBy, invalid}. */
export function Field({ label, hint, error, count, max, optional, children, className = '' }) {
  const id = useId()
  const errId = `${id}-err`
  const hintId = `${id}-hint`
  const over = max != null && count > max
  return (
    <div className={className}>
      <div className="flex items-baseline justify-between gap-2">
        <label htmlFor={id} className="label">
          {label}
          {optional && <span className="ml-1.5 font-normal text-faint">Optional</span>}
        </label>
        {max != null && (
          <span className={`tnum text-xs ${over ? 'text-danger font-medium' : 'text-faint'}`} aria-live="polite">
            {count.toLocaleString()} / {max.toLocaleString()}
          </span>
        )}
      </div>
      {children({ id, invalid: Boolean(error), describedBy: [error ? errId : null, hint ? hintId : null].filter(Boolean).join(' ') || undefined })}
      {hint && !error && (
        <p id={hintId} className="hint mt-1.5">
          {hint}
        </p>
      )}
      {error && (
        <p id={errId} role="alert" className="mt-1.5 flex items-start gap-1.5 text-sm text-danger">
          <AlertCircle size={14} className="mt-[3px] shrink-0" aria-hidden />
          <span>{error}</span>
        </p>
      )}
    </div>
  )
}

export function Skeleton({ className = '' }) {
  return <div className={`animate-pulse rounded bg-subtle ${className}`} aria-hidden />
}

export function EmptyState({ icon: Icon, title, children, action }) {
  return (
    <div className="flex flex-col items-center justify-center px-6 py-16 text-center">
      {Icon && (
        <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-lg border border-line bg-surface text-muted">
          <Icon size={20} strokeWidth={1.75} aria-hidden />
        </div>
      )}
      <h3 className="text-md font-semibold text-ink">{title}</h3>
      {children && <div className="mt-1.5 max-w-md text-base text-muted">{children}</div>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  )
}

export function PageHeader({ title, description, actions }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div className="min-w-0">
        <h1 className="text-2xl font-semibold tracking-tight text-ink">{title}</h1>
        {description && <p className="mt-1 text-base text-muted">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  )
}

export function Spinner({ size = 14 }) {
  // Only used inside buttons while an action is in flight (pages use skeletons).
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" className="animate-spin" aria-hidden>
      <circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" strokeOpacity="0.25" strokeWidth="3" />
      <path d="M21 12a9 9 0 0 0-9-9" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
  )
}
