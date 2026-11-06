import { animate } from 'framer-motion'
import { useEffect, useRef } from 'react'

const reduceMotion = () =>
  typeof window !== 'undefined' && window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches

/**
 * A number that counts up from 0 on first render and tweens smoothly when the
 * value changes. Writes straight to the DOM node so it never re-renders React.
 */
export default function AnimatedNumber({ value, decimals = 1, duration = 0.6, delay = 0, fromZero = true, className = '' }) {
  const ref = useRef(null)
  const last = useRef(fromZero ? 0 : value)

  useEffect(() => {
    const node = ref.current
    if (!node) return undefined
    const from = last.current
    last.current = value
    if (reduceMotion() || from === value) {
      node.textContent = Number(value).toFixed(decimals)
      return undefined
    }
    const controls = animate(from, value, {
      duration,
      delay,
      ease: [0.16, 1, 0.3, 1],
      onUpdate: (v) => {
        node.textContent = v.toFixed(decimals)
      },
    })
    return () => controls.stop()
  }, [value]) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <span ref={ref} className={`tnum ${className}`}>
      {Number(fromZero ? 0 : value).toFixed(decimals)}
    </span>
  )
}
