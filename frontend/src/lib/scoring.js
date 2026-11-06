// Client-side mirror of backend/app/engine/scoring.py, used by the
// "what if" weights panel to re-rank instantly without re-running the match.
// Uses the SAME integer-tenths arithmetic as the server so numbers agree exactly.

export const DEFAULT_WEIGHTS = { skills: 40, experience: 25, education: 15, semantic: 20 }
export const WEIGHT_KEYS = ['skills', 'experience', 'education', 'semantic']

export const METRICS = [
  { key: 'skills', field: 'skills_score', label: 'Skills', long: 'Skills match' },
  { key: 'experience', field: 'experience_score', label: 'Experience', long: 'Experience' },
  { key: 'education', field: 'education_score', label: 'Education', long: 'Education' },
  { key: 'semantic', field: 'semantic_score', label: 'Meaning', long: 'Meaning match' },
]

export const weightTotal = (w) => WEIGHT_KEYS.reduce((sum, k) => sum + (Number(w[k]) || 0), 0)

/** Overall = (skills*ws + experience*we + education*wd + semantic*wm) / 100, 1 dp, half up. */
export function overallScore(row, w) {
  const tenths = [row.skills_score, row.experience_score, row.education_score, row.semantic_score].map((c) =>
    Math.round(c * 10),
  )
  const ws = [w.skills, w.experience, w.education, w.semantic]
  const total = tenths.reduce((sum, t, i) => sum + t * ws[i], 0)
  return Math.floor((total + 50) / 100) / 10
}

/** Ranking: overall desc, skills desc, name A-Z, then id (same as the server). */
export function compareRows(a, b) {
  if (b.overall_score !== a.overall_score) return b.overall_score - a.overall_score
  if (b.skills_score !== a.skills_score) return b.skills_score - a.skills_score
  const an = a.full_name.toLowerCase()
  const bn = b.full_name.toLowerCase()
  if (an !== bn) return an < bn ? -1 : 1
  return a.candidate_id - b.candidate_id
}

/** Recompute overall for every row with new weights and return a new ranked array. */
export function rerank(rows, weights) {
  const next = rows.map((r) => ({ ...r, overall_score: overallScore(r, weights) }))
  next.sort(compareRows)
  return next.map((r, i) => ({ ...r, rank: i + 1 }))
}

export function fmt(n) {
  return Number(n).toFixed(1)
}

const short = (x) => {
  const s = Number(x).toFixed(1)
  return s.endsWith('.0') ? s.slice(0, -2) : s
}

/** "Overall = (90×40 + 100×25 + ...) / 100 = 90.2" for the given weights. */
export function calculation(row, w) {
  return (
    `Overall = (${short(row.skills_score)}×${w.skills} + ${short(row.experience_score)}×${w.experience}` +
    ` + ${short(row.education_score)}×${w.education} + ${short(row.semantic_score)}×${w.semantic}) / 100` +
    ` = ${fmt(overallScore(row, w))}`
  )
}

/**
 * Change one weight and rebalance the others so the total stays at 100.
 * The difference is spread across the other weights in proportion to their
 * current size (largest-remainder rounding keeps everything whole numbers).
 */
export function rebalance(weights, key, value) {
  const v = Math.max(0, Math.min(100, Math.round(Number(value) || 0)))
  const others = WEIGHT_KEYS.filter((k) => k !== key)
  const remaining = 100 - v
  const currentOthers = others.reduce((s, k) => s + weights[k], 0)
  const raw = others.map((k) =>
    currentOthers > 0 ? (weights[k] / currentOthers) * remaining : remaining / others.length,
  )
  const floored = raw.map(Math.floor)
  const left = remaining - floored.reduce((a, b) => a + b, 0)
  const order = raw.map((r, i) => [r - floored[i], i]).sort((a, b) => b[0] - a[0] || a[1] - b[1])
  for (let j = 0; j < left; j++) floored[order[j % order.length][1]] += 1
  const out = { ...weights, [key]: v }
  others.forEach((k, i) => {
    out[k] = floored[i]
  })
  return out
}

/** Weights stored on a job or run -> {skills, experience, education, semantic}. */
export const weightsOf = (o) => ({
  skills: o.w_skills,
  experience: o.w_experience,
  education: o.w_education,
  semantic: o.w_semantic,
})

export const toWeightFields = (w) => ({
  w_skills: Number(w.skills),
  w_experience: Number(w.experience),
  w_education: Number(w.education),
  w_semantic: Number(w.semantic),
})

export const sameWeights = (a, b) => WEIGHT_KEYS.every((k) => Number(a[k]) === Number(b[k]))
