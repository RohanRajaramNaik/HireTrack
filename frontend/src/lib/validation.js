// Client-side validation that mirrors the server's Pydantic rules, so users
// see the same message inline before anything is sent.
import { weightTotal } from './scoring'

// Small built-in fallback, used until the real table arrives from the server
// (see setSkillAliases below) or if that fetch never completes. The server's
// backend/app/engine/skills.py table is the source of truth and is much
// larger; without it, two different spellings of the same skill can look
// fine client-side and still be rejected as duplicates when the job is saved.
const FALLBACK_ALIASES = {
  js: 'javascript',
  ts: 'typescript',
  py: 'python',
  k8s: 'kubernetes',
  postgres: 'postgresql',
  ml: 'machine learning',
  node: 'node.js',
  nodejs: 'node.js',
  reactjs: 'react',
  golang: 'go',
}

let ALIASES = FALLBACK_ALIASES

/** Replace the alias table with the one fetched from GET /api/skill-aliases. */
export function setSkillAliases(aliases) {
  ALIASES = { ...FALLBACK_ALIASES, ...aliases }
}

export function normaliseSkill(s) {
  const c = String(s).trim().toLowerCase().replace(/\s+/g, ' ')
  return ALIASES[c] || c
}

const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/
const PHONE_RE = /^\+?[0-9 ()-]{7,20}$/

function numberError(value, label, min = 0, max = 50) {
  if (value === '' || value === null || value === undefined) return `${label} is required`
  const n = Number(value)
  if (Number.isNaN(n)) return `${label} must be a number`
  if (n < min) return `${label} cannot be less than ${min}`
  if (n > max) return `${label} cannot be more than ${max}`
  return null
}

function textError(value, label, min, max) {
  const t = (value || '').trim()
  if (!t) return `${label} is required`
  if (t.length < min) return min <= 2 ? `${label} must be at least ${min} characters` : `${label} must be at least ${min} characters (now ${t.length})`
  if (t.length > max) return `${label} must be ${max} characters or fewer`
  return null
}

export function validateCandidate(v) {
  const e = {}
  const name = textError(v.full_name, 'Full name', 2, 100)
  if (name) e.full_name = name
  if (v.email && !EMAIL_RE.test(v.email.trim())) e.email = 'Enter a valid email address, or leave it blank'
  if (v.phone && !PHONE_RE.test(v.phone.trim())) e.phone = 'Enter a valid phone number (digits, spaces, +, - and brackets only)'
  const yrs = numberError(v.years_experience, 'Years of experience')
  if (yrs) e.years_experience = yrs
  if (!v.level_id) e.level_id = 'Choose an education level'
  const summary = textError(v.resume_summary, 'Resume summary', 20, 3000)
  if (summary) e.resume_summary = summary
  if (!v.skills || v.skills.filter((s) => s.trim()).length === 0) e.skills = 'Add at least one skill'
  return e
}

export function validateJob(v) {
  const e = {}
  const title = textError(v.job_title, 'Job title', 2, 100)
  if (title) e.job_title = title
  const loc = textError(v.location, 'Location', 2, 80)
  if (loc) e.location = loc
  const exp = numberError(v.min_experience, 'Minimum experience')
  if (exp) e.min_experience = exp
  if (!v.min_level_id) e.min_level_id = 'Choose a minimum education level'
  const desc = textError(v.job_description, 'Job description', 20, 5000)
  if (desc) e.job_description = desc
  const req = (v.required_skills || []).map(normaliseSkill).filter(Boolean)
  const pref = (v.preferred_skills || []).map(normaliseSkill).filter(Boolean)
  if (req.length === 0) e.required_skills = 'Add at least one required skill'
  const overlap = [...new Set(pref.filter((p) => req.includes(p)))]
  if (overlap.length) e.preferred_skills = `Preferred skills repeat required skills: ${overlap.join(', ')}`
  const w = v.weights || {}
  const bad = Object.values(w).some((x) => x === '' || !Number.isInteger(Number(x)) || Number(x) < 0 || Number(x) > 100)
  if (bad) e.weights = 'Each weight must be a whole number from 0 to 100'
  else if (weightTotal(w) !== 100) e.weights = `Weights must add up to 100% (now ${weightTotal(w)}%)`
  return e
}
