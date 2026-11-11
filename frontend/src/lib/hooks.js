import { useEffect, useState } from 'react'
import { api } from '../apiClient'
import { setSkillAliases } from './validation'

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

let aliasesFetched = false

/** Loads the server's skill alias table once, so client-side duplicate
 * checks (TagInput, job validation, candidate search) agree with the
 * server instead of relying on the small built-in fallback list. */
export function useSkillAliases() {
  useEffect(() => {
    if (aliasesFetched) return
    aliasesFetched = true
    api
      .skillAliases()
      .then(setSkillAliases)
      .catch(() => {
        aliasesFetched = false
      })
  }, [])
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
