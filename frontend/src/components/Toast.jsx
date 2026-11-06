import { AnimatePresence, motion } from 'framer-motion'
import { CheckCircle2, Info, X, XCircle } from 'lucide-react'
import { createContext, useCallback, useContext, useMemo, useRef, useState } from 'react'

const ToastContext = createContext(null)

const ICONS = {
  success: <CheckCircle2 size={16} className="text-go" aria-hidden />,
  error: <XCircle size={16} className="text-danger" aria-hidden />,
  info: <Info size={16} className="text-accent" aria-hidden />,
}

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])
  const nextId = useRef(1)

  const dismiss = useCallback((id) => setToasts((t) => t.filter((x) => x.id !== id)), [])

  const push = useCallback(
    (kind, title, body) => {
      const id = nextId.current++
      setToasts((t) => [...t.slice(-3), { id, kind, title, body }])
      setTimeout(() => dismiss(id), kind === 'error' ? 6500 : 4000)
    },
    [dismiss],
  )

  const value = useMemo(
    () => ({
      success: (title, body) => push('success', title, body),
      error: (title, body) => push('error', title, body),
      info: (title, body) => push('info', title, body),
    }),
    [push],
  )

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div
        className="pointer-events-none fixed bottom-4 right-4 z-[80] flex w-[22rem] max-w-[calc(100vw-2rem)] flex-col gap-2"
        aria-live="polite"
        role="status"
      >
        <AnimatePresence initial={false}>
          {toasts.map((t) => (
            <motion.div
              key={t.id}
              layout
              initial={{ opacity: 0, y: 12, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, x: 24, transition: { duration: 0.15 } }}
              transition={{ duration: 0.2, ease: 'easeOut' }}
              className="pointer-events-auto flex items-start gap-3 rounded-lg border border-line bg-surface px-3.5 py-3 shadow-pop"
            >
              <span className="mt-0.5">{ICONS[t.kind]}</span>
              <div className="min-w-0 flex-1">
                <p className="text-base font-medium text-ink">{t.title}</p>
                {t.body && <p className="mt-0.5 text-sm text-muted">{t.body}</p>}
              </div>
              <button
                type="button"
                onClick={() => dismiss(t.id)}
                className="-mr-1 rounded p-0.5 text-faint hover:bg-subtle hover:text-ink"
                aria-label="Dismiss notification"
              >
                <X size={14} />
              </button>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  )
}

export function useToast() {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be used inside ToastProvider')
  return ctx
}
