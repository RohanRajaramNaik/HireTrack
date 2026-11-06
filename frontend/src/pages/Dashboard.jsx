import { motion } from 'framer-motion'
import { ArrowRight, Briefcase, ChevronRight, PlayCircle, Plus } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../apiClient'
import { Skeleton, Spinner } from '../components/ui'
import { useToast } from '../components/Toast'
import { capitalise, timeAgo } from '../lib/format'
import { demoState } from '../lib/hooks'

function Tile({ label, value, sub, index }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: index * 0.05, ease: 'easeOut' }}
      className="bg-surface px-5 py-4"
    >
      <p className="text-sm text-muted">{label}</p>
      <p className="tnum mt-2 text-3xl font-semibold tracking-tight text-ink">{value}</p>
      <p className="mt-1 truncate text-sm text-faint">{sub}</p>
    </motion.div>
  )
}

const COMPONENTS = [
  ['Skills', 'Required skills count for 80 points, preferred for 20. Aliases like JS and JavaScript count as the same skill.'],
  ['Experience', 'Full marks at or above the minimum years, otherwise in proportion.'],
  ['Education', 'Full marks at or above the minimum level, otherwise in proportion.'],
  ['Meaning match', 'How closely the CV summary describes the work in the job description, even in different words.'],
]

export default function Dashboard() {
  const [stats, setStats] = useState(null)
  const [jobs, setJobs] = useState(null)
  const [starting, setStarting] = useState(false)
  const navigate = useNavigate()
  const toast = useToast()

  useEffect(() => {
    api.stats().then(setStats).catch((e) => toast.error('Could not load the dashboard', e.detail))
    api.listJobs().then(setJobs).catch(() => setJobs([]))
  }, [toast])

  const startDemo = async () => {
    setStarting(true)
    try {
      const r = await api.demoStart()
      if (r.seeded) toast.info('Demo data loaded', '18 candidates and 3 job specifications are ready.')
      demoState.tourPending = true
      navigate(`/jobs/${r.job_id}`, { state: { demo: true } })
    } catch (e) {
      toast.error('Could not start the guided demo', e.detail)
      setStarting(false)
    }
  }

  const tiles = stats
    ? [
        { label: 'Candidates in database', value: stats.candidates.toLocaleString(), sub: stats.candidates ? 'Ready to match' : 'None yet. Add or load demo data.' },
        { label: 'Open jobs', value: stats.jobs.toLocaleString(), sub: stats.jobs ? 'Job specifications saved' : 'Create your first job' },
        { label: 'Last match run', value: stats.last_run_at ? capitalise(timeAgo(stats.last_run_at)) : 'Never', sub: stats.last_run_job_title || 'No matches run yet' },
        { label: 'Average match score', value: stats.average_score != null ? stats.average_score.toFixed(1) : '–', sub: stats.average_score != null ? 'Across the last run, out of 100' : 'Shown after your first run' },
      ]
    : null

  return (
    <div className="space-y-8">
      <section className="flex flex-wrap items-end justify-between gap-6">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-ink">Dashboard</h1>
          <p className="mt-1 max-w-xl text-base text-muted">
            Rank every candidate against a job specification and see exactly why each one placed where they did.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button type="button" className="btn-secondary btn-lg" onClick={startDemo} disabled={starting} data-testid="start-demo">
            {starting ? <Spinner /> : <PlayCircle size={18} aria-hidden />}
            Start guided demo
          </button>
          <Link to="/jobs/new" className="btn-primary btn-lg">
            <Plus size={18} aria-hidden />
            Create a job and find matches
          </Link>
        </div>
      </section>

      <section aria-label="Summary" className="grid grid-cols-2 gap-px overflow-hidden rounded-lg border border-line bg-line lg:grid-cols-4">
        {tiles
          ? tiles.map((t, i) => <Tile key={t.label} index={i} {...t} />)
          : [0, 1, 2, 3].map((i) => (
              <div key={i} className="bg-surface px-5 py-4">
                <Skeleton className="h-4 w-32" />
                <Skeleton className="mt-3 h-9 w-20" />
                <Skeleton className="mt-2 h-4 w-40" />
              </div>
            ))}
      </section>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
        <section className="panel">
          <div className="flex items-center justify-between border-b border-line px-5 py-3">
            <h2 className="text-md font-semibold text-ink">Job specifications</h2>
            <Link to="/jobs" className="inline-flex items-center gap-1 text-sm font-medium text-accent hover:underline">
              All jobs <ArrowRight size={14} aria-hidden />
            </Link>
          </div>
          {jobs === null ? (
            <div className="space-y-3 p-5">
              {[0, 1, 2].map((i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : jobs.length === 0 ? (
            <div className="px-5 py-10 text-center">
              <Briefcase size={20} className="mx-auto text-faint" aria-hidden />
              <p className="mt-3 text-base font-medium text-ink">No job specifications yet</p>
              <p className="mt-1 text-sm text-muted">Create one, or start the guided demo to load three sample jobs.</p>
            </div>
          ) : (
            <ul className="divide-y divide-line">
              {jobs.slice(0, 6).map((j) => (
                <li key={j.job_id}>
                  <Link
                    to={j.last_run_at ? `/results/${j.job_id}` : `/jobs/${j.job_id}`}
                    className="group flex items-center gap-4 px-5 py-3 hover:bg-canvas"
                  >
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-base font-medium text-ink">{j.job_title}</p>
                      <p className="truncate text-sm text-faint">
                        {j.required_skills.length} required · {j.preferred_skills.length} preferred · min {j.min_experience} yrs ·{' '}
                        {j.min_level_name}
                      </p>
                    </div>
                    <span className="hidden text-sm text-muted sm:block">
                      {j.last_run_at ? `Matched ${timeAgo(j.last_run_at)}` : 'Not matched yet'}
                    </span>
                    <ChevronRight size={16} className="text-faint transition-transform group-hover:translate-x-0.5" aria-hidden />
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="panel">
          <div className="border-b border-line px-5 py-3">
            <h2 className="text-md font-semibold text-ink">How a match is scored</h2>
          </div>
          <dl className="divide-y divide-line">
            {COMPONENTS.map(([name, text]) => (
              <div key={name} className="px-5 py-3">
                <dt className="text-base font-medium text-ink">{name}</dt>
                <dd className="mt-0.5 text-sm text-muted">{text}</dd>
              </div>
            ))}
          </dl>
          <p className="border-t border-line px-5 py-3 text-sm text-muted">
            Each job sets how much the four parts count. Names, emails and personal details are never scored.
          </p>
        </section>
      </div>
    </div>
  )
}
