import { AnimatePresence, motion } from 'framer-motion'
import { AlertTriangle, X } from 'lucide-react'
import { useEffect, useId, useRef } from 'react'

const FOCUSABLE = 'a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])'

// Only the top-most open dialog reacts to Escape/Tab (a confirm dialog can
// open on top of a slide-over).
const stack = []

/** Keeps Tab focus inside `ref`, closes on Escape, restores focus on close. */
function useDialogFocus(open, ref, onClose, initialFocus) {
  useEffect(() => {
    if (!open) return undefined
    const token = {}
    stack.push(token)
    const previous = document.activeElement
    const t = setTimeout(() => {
      const el = (initialFocus && initialFocus.current) || ref.current?.querySelector(FOCUSABLE)
      el?.focus()
    }, 30)
    const onKey = (e) => {
      if (stack[stack.length - 1] !== token) return
      if (e.key === 'Escape') {
        e.stopPropagation()
        onClose?.()
      } else if (e.key === 'Tab' && ref.current) {
        const items = [...ref.current.querySelectorAll(FOCUSABLE)].filter((n) => n.offsetParent !== null)
        if (!items.length) return
        const first = items[0]
        const last = items[items.length - 1]
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault()
          last.focus()
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault()
          first.focus()
        }
      }
    }
    document.addEventListener('keydown', onKey)
    return () => {
      clearTimeout(t)
      stack.splice(stack.indexOf(token), 1)
      document.removeEventListener('keydown', onKey)
      if (previous && previous.focus) previous.focus()
    }
  }, [open]) // eslint-disable-line react-hooks/exhaustive-deps
}

/** Right-hand slide-over panel. */
export function SlideOver({ open, onClose, title, subtitle, children, footer, width = 'w-[34rem]', modal = true, tourId }) {
  const ref = useRef(null)
  const titleId = useId()
  useDialogFocus(open && modal, ref, onClose)
  return (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-50 flex justify-end" role="presentation">
          <motion.div
            className="absolute inset-0 bg-ink/25"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.18 }}
            onClick={onClose}
          />
          <motion.section
            ref={ref}
            role="dialog"
            aria-modal="true"
            aria-labelledby={titleId}
            data-tour={tourId}
            className={`relative flex h-full ${width} max-w-[calc(100vw-2rem)] flex-col border-l border-line bg-surface shadow-panel`}
            initial={{ x: 48, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: 48, opacity: 0 }}
            transition={{ type: 'tween', duration: 0.22, ease: [0.2, 0.8, 0.2, 1] }}
          >
            <header className="flex items-start justify-between gap-4 border-b border-line px-6 py-4">
              <div className="min-w-0">
                <h2 id={titleId} className="truncate text-lg font-semibold text-ink">
                  {title}
                </h2>
                {subtitle && <p className="mt-0.5 text-sm text-muted">{subtitle}</p>}
              </div>
              <button type="button" onClick={onClose} className="btn-ghost btn-sm -mr-2 px-1.5" aria-label="Close panel">
                <X size={18} />
              </button>
            </header>
            <div className="flex-1 overflow-y-auto px-6 py-5">{children}</div>
            {footer && <footer className="flex items-center gap-2 border-t border-line bg-canvas px-6 py-3">{footer}</footer>}
          </motion.section>
        </div>
      )}
    </AnimatePresence>
  )
}

/** Centered confirmation dialog. `tone="danger"` uses the red button. */
export function ConfirmDialog({ open, title, children, confirmLabel = 'Confirm', tone = 'danger', busy, onConfirm, onCancel, confirmDisabled }) {
  const ref = useRef(null)
  const cancelRef = useRef(null)
  const titleId = useId()
  useDialogFocus(open, ref, onCancel, cancelRef)
  return (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
          <motion.div
            className="absolute inset-0 bg-ink/30"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            onClick={onCancel}
          />
          <motion.div
            ref={ref}
            role="alertdialog"
            aria-modal="true"
            aria-labelledby={titleId}
            className="relative w-full max-w-md rounded-lg border border-line bg-surface shadow-pop"
            initial={{ opacity: 0, scale: 0.97, y: 6 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.98 }}
            transition={{ duration: 0.16, ease: 'easeOut' }}
          >
            <div className="flex gap-3 px-5 pb-4 pt-5">
              {tone === 'danger' && (
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-danger-soft text-danger">
                  <AlertTriangle size={16} aria-hidden />
                </div>
              )}
              <div className="min-w-0 flex-1">
                <h2 id={titleId} className="text-md font-semibold text-ink">
                  {title}
                </h2>
                <div className="mt-1.5 text-base text-muted">{children}</div>
              </div>
            </div>
            <div className="flex justify-end gap-2 rounded-b-lg border-t border-line bg-canvas px-5 py-3">
              <button ref={cancelRef} type="button" className="btn-secondary" onClick={onCancel} disabled={busy}>
                Cancel
              </button>
              <button
                type="button"
                className={tone === 'danger' ? 'btn-danger' : 'btn-primary'}
                onClick={onConfirm}
                disabled={busy || confirmDisabled}
              >
                {busy ? 'Working…' : confirmLabel}
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  )
}
