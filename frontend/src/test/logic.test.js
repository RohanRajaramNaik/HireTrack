import { describe, expect, it } from 'vitest'
import { calculation, overallScore, rebalance, rerank } from '../lib/scoring'
import { validateCandidate, validateJob } from '../lib/validation'

const W = { skills: 40, experience: 25, education: 15, semantic: 20 }
const row = (id, name, s, e, d, m) => ({
  candidate_id: id,
  full_name: name,
  skills_score: s,
  experience_score: e,
  education_score: d,
  semantic_score: m,
})

describe('client-side scoring (must match the Python engine exactly)', () => {
  it('computes overall with the default weights', () => {
    // Same cases as backend/tests/test_scoring.py
    expect(overallScore(row(1, 'A', 90, 100, 75, 60), W)).toBe(84.3)
    expect(overallScore(row(1, 'A', 63.3, 50, 66.7, 41.2), W)).toBe(56.1)
    expect(overallScore(row(1, 'A', 100, 100, 100, 62.3), W)).toBe(92.5)
  })

  it('rounds half up, not half even', () => {
    // (0.5*... ) chosen so the exact result is x.x5
    expect(overallScore(row(1, 'A', 0.5, 0, 0, 0), { skills: 50, experience: 50, education: 0, semantic: 0 })).toBe(0.3)
  })

  it('builds the calculation string', () => {
    expect(calculation(row(1, 'A', 100, 100, 100, 62.3), W)).toBe(
      'Overall = (100×40 + 100×25 + 100×15 + 62.3×20) / 100 = 92.5',
    )
  })
})

describe('rerank', () => {
  const rows = [
    row(1, 'Skills Heavy', 100, 40, 50, 30),
    row(2, 'Meaning Heavy', 40, 100, 100, 90),
    row(3, 'Balanced', 70, 70, 70, 70),
  ]

  it('changes order when weights change', () => {
    const skillsFirst = rerank(rows, { skills: 100, experience: 0, education: 0, semantic: 0 })
    expect(skillsFirst.map((r) => r.candidate_id)).toEqual([1, 3, 2])
    const meaningFirst = rerank(rows, { skills: 0, experience: 0, education: 0, semantic: 100 })
    expect(meaningFirst.map((r) => r.candidate_id)).toEqual([2, 3, 1])
    expect(meaningFirst.map((r) => r.rank)).toEqual([1, 2, 3])
  })

  it('breaks ties on skills, then name A-Z', () => {
    const tied = [row(1, 'Zanele', 50, 50, 50, 50), row(2, 'andile', 50, 50, 50, 50), row(3, 'Bongani', 60, 40, 50, 50)]
    const out = rerank(tied, { skills: 0, experience: 0, education: 100, semantic: 0 })
    expect(out.map((r) => r.full_name)).toEqual(['Bongani', 'andile', 'Zanele'])
  })

  it('does not mutate the input', () => {
    const copy = JSON.stringify(rows)
    rerank(rows, W)
    expect(JSON.stringify(rows)).toBe(copy)
  })
})

describe('rebalance', () => {
  it('always totals 100 with whole numbers', () => {
    for (const v of [0, 1, 33, 50, 77, 99, 100]) {
      const out = rebalance(W, 'skills', v)
      expect(out.skills).toBe(v)
      expect(Object.values(out).reduce((a, b) => a + b, 0)).toBe(100)
      Object.values(out).forEach((x) => expect(Number.isInteger(x)).toBe(true))
    }
  })

  it('spreads evenly when the others are all zero', () => {
    const out = rebalance({ skills: 100, experience: 0, education: 0, semantic: 0 }, 'skills', 40)
    expect(out).toEqual({ skills: 40, experience: 20, education: 20, semantic: 20 })
  })
})

describe('form validation', () => {
  const goodCandidate = {
    full_name: 'Thandiwe Nkosi',
    email: '',
    years_experience: 4,
    level_id: '4',
    resume_summary: 'Builds data pipelines in Python and SQL on AWS.',
    skills: ['Python'],
  }

  it('accepts a valid candidate', () => {
    expect(validateCandidate(goodCandidate)).toEqual({})
  })

  it('rejects negative years, empty name, short summary, no skills and bad email', () => {
    const e = validateCandidate({ ...goodCandidate, years_experience: -1, full_name: ' ', resume_summary: 'short', skills: [], email: 'x@' })
    expect(e.years_experience).toBe('Years of experience cannot be less than 0')
    expect(e.full_name).toBe('Full name is required')
    expect(e.resume_summary).toMatch(/at least 20 characters/)
    expect(e.skills).toBe('Add at least one skill')
    expect(e.email).toMatch(/valid email/)
  })

  const goodJob = {
    job_title: 'Data Engineer',
    min_experience: 3,
    min_level_id: '4',
    job_description: 'Design and run data pipelines on AWS for analytics.',
    required_skills: ['Python'],
    preferred_skills: ['AWS'],
    weights: { ...W },
  }

  it('accepts a valid job', () => {
    expect(validateJob(goodJob)).toEqual({})
  })

  it('gives the exact weights message at 95%', () => {
    expect(validateJob({ ...goodJob, weights: { ...W, semantic: 15 } }).weights).toBe('Weights must add up to 100% (now 95%)')
  })

  it('rejects preferred skills that repeat a required one, including aliases', () => {
    expect(validateJob({ ...goodJob, required_skills: ['JavaScript'], preferred_skills: ['JS'] }).preferred_skills).toBe(
      'Preferred skills repeat required skills: javascript',
    )
  })

  it('requires at least one required skill', () => {
    expect(validateJob({ ...goodJob, required_skills: [] }).required_skills).toBe('Add at least one required skill')
  })
})
