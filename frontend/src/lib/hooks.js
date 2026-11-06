import { useEffect, useState } from 'react'
import { api } from '../apiClient'

let levelsCache = null

/** Education levels rarely change: fetch once per page load. */
export function useEducationLevels() {
  const [levels, setLevels] = useState(levelsCache || [])
  useEffect(() => {
    if (levelsCache) return
    api
      .educationLevels()
      .then((l) => {
        levelsCache = l
        setLevels(l)
      })
      .catch(() => {})
  }, [])
  return levels
}

export function useDebounced(value, ms = 150) {
  const [v, setV] = useState(value)
  useEffect(() => {
    const t = setTimeout(() => setV(value), ms)
    return () => clearTimeout(t)
  }, [value, ms])
  return v
}

/** Shared flag so Jobs -> Results can hand over "start the tour" without URL noise. */
export const demoState = { tourPending: false }
