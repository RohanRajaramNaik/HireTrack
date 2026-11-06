import { AnimatePresence, motion } from 'framer-motion'
import { ArrowLeft, ArrowRight, X } from 'lucide-react'
import { useEffect, useLayoutEffect, useRef, useState } from 'react'

const PAD = 8
const CARD_W = 340

/**
 * Lightweight guided tour. Each step points at an element by CSS selector
 * (we use data-tour="..." attributes), dims the rest of the page and shows a
 * short explanation. The page under the spotlight stays interactive so the
 * presenter can, for example, drag the weight sliders during the last step.
 *
 * Keys: Right/Enter = next, Left = back, Esc = end tour.
 */
export default function Tour({ steps, open, onClose }) {
  const [index, setIndex] = useState(0)
  const [rect, setRect] = useState(null)
  const cardRef = useRef(null)
  const [cardH, setCardH] = useState(180)
  const step = steps[index]

  useEffect(() => {
    if (open) setIndex(0)
  }, [open])

  // Run the step's setup (open a panel, expand weights...) when it starts.
  useEffect(() => {
    if (open && step?.onEnter) step.onEnter()
  }, [open, index]) // eslint-disable-line react-hooks/exhaustive-deps

  // Follow the target as panels animate, the page scrolls or the window resizes.
  useEffect(() => {
    if (!open || !step) return undefined
    let frame
    let scrolled = false
    const tick = () => {
      const el = document.querySelector(step.target)
      if (el) {
        if (!scrolled) {
          const r0 = el.getBoundingClientRect()
          if (r0.top < 64 || r0.bottom > window.innerHeight) el.scrollIntoView({ block: 'center', behavior: 'smooth' })
          scrolled = true
        }
        const r = el.getBoundingClientRect()
        setRect((prev) =>
          prev && Math.abs(prev.top - r.top) < 0.5 && Math.abs(prev.left - r.left) < 0.5 && Math.abs(prev.width - r.width) < 0.5 && Math.abs(prev.height - r.height) < 0.5
            ? prev
            : { top: r.top, left: r.left, width: r.width, height: r.height },
        )
      } else setRect(null)
      frame = requestAnimationFrame(tick)
    }
    tick()
    return () => cancelAnimationFrame(frame)
  }, [open, index]) // eslint-disable-line react-hooks/exhaustive-deps

  useLayoutEffect(() => {
    if (cardRef.current) setCardH(cardRef.current.offsetHeight)
  }, [index, open, rect?.width])

  useEffect(() => {
    if (!open) return undefined
    const onKey = (e) => {
      if (['INPUT', 'TEXTAREA'].includes(document.activeElement?.tagName) && e.key !== 'Escape') return
      if (e.key === 'Escape') onClose()
      else if (e.key === 'ArrowRight' || e.key === 'Enter') {
        e.preventDefault()
        next()
      } else if (e.key === 'ArrowLeft') setIndex((i) => Math.max(0, i - 1))
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }) // eslint-disable-line react-hooks/exhaustive-deps

  const next = () => (index < steps.length - 1 ? setIndex(index + 1) : onClose())

  if (!open || !step) return null

  const vw = window.innerWidth
  const vh = window.innerHeight
  let cardPos
  if (rect) {
    const placement = step.placement || 'auto'
    const spaceRight = vw - (rect.left + rect.width)
    const spaceLeft = rect.left
    const clampTop = (t) => Math.max(72, Math.min(vh - cardH - 16, t))
    if ((placement === 'left' || (placement === 'auto' && spaceLeft > CARD_W + 32 && spaceRight < CARD_W + 32)) && spaceLeft > CARD_W + 24) {
      cardPos = { top: clampTop(rect.top), left: rect.left - CARD_W - 20 }
    } else if ((placement === 'right' || placement === 'auto') && spaceRight > CARD_W + 24) {
      cardPos = { top: clampTop(rect.top), left: rect.left + rect.width + 20 }
    } else if (rect.top + rect.height + cardH + 24 < vh) {
      cardPos = { top: rect.top + rect.height + 16, left: Math.max(16, Math.min(vw - CARD_W - 16, rect.left)) }
    } else {
      cardPos = { top: Math.max(72, rect.top - cardH - 16), left: Math.max(16, Math.min(vw - CARD_W - 16, rect.left)) }
    }
  } else {
    cardPos = { top: vh / 2 - cardH / 2, left: vw / 2 - CARD_W / 2 }
  }

  return (
    <div className="pointer-events-none fixed inset-0 z-[70]" aria-live="polite">
      <motion.div
        className="absolute rounded-lg ring-2 ring-accent"
        initial={false}
        animate={
          rect
            ? { top: rect.top - PAD, left: rect.left - PAD, width: rect.width + PAD * 2, height: rect.height + PAD * 2, opacity: 1 }
            : { top: vh / 2, left: vw / 2, width: 0, height: 0, opacity: 1 }
        }
        transition={{ type: 'spring', stiffness: 320, damping: 34 }}
        style={{ boxShadow: '0 0 0 9999px rgb(15 23 42 / 0.45)' }}
      />
      <AnimatePresence mode="wait">
        <motion.div
          key={index}
          ref={cardRef}
          role="dialog"
          aria-label={`Guided demo step ${index + 1} of ${steps.length}: ${step.title}`}
          className="pointer-events-auto absolute rounded-lg border border-line bg-surface p-4 shadow-pop"
          style={{ width: CARD_W, top: cardPos.top, left: cardPos.left }}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -4 }}
          transition={{ duration: 0.18 }}
        >
          <div className="flex items-start justify-between gap-3">
            <p className="tnum text-xs font-medium uppercase tracking-wide text-accent">
              Step {index + 1} of {steps.length}
            </p>
            <button type="button" onClick={onClose} className="-mr-1 -mt-1 rounded p-1 text-faint hover:bg-subtle hover:text-ink" aria-label="End guided demo">
              <X size={14} />
            </button>
          </div>
          <h3 className="mt-1 text-md font-semibold text-ink">{step.title}</h3>
          <div className="mt-1.5 text-base text-muted">{step.body}</div>
          <div className="mt-4 flex items-center justify-between">
            <div className="flex gap-1" aria-hidden>
              {steps.map((_, i) => (
                <span key={i} className={`h-1.5 w-4 rounded-full ${i === index ? 'bg-accent' : 'bg-line'}`} />
              ))}
            </div>
            <div className="flex gap-2">
              {index > 0 && (
                <button type="button" className="btn-ghost btn-sm" onClick={() => setIndex(index - 1)}>
                  <ArrowLeft size={14} aria-hidden /> Back
                </button>
              )}
              <button type="button" className="btn-primary btn-sm" onClick={next} autoFocus>
                {index < steps.length - 1 ? (
                  <>
                    Next <ArrowRight size={14} aria-hidden />
                  </>
                ) : (
                  'Finish'
                )}
              </button>
            </div>
          </div>
        </motion.div>
      </AnimatePresence>
    </div>
  )
}
