import { motion } from 'framer-motion'
import { ArrowRight, PlayCircle, Plus } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../apiClient'
import { ColumnChart, HBarChart } from '../components/Charts'
import { useToast } from '../components/Toast'
import { Skeleton, Spinner } from '../components/ui'
import { ROLE_LABELS, useAuth } from '../lib/auth'
import { capitalise, timeAgo } from '../lib/format'
import { demoState } from '../lib/hooks'
import { STAGE_LABELS } from '../lib/stages'

function Tile({ label, value, sub, index, to }) {
  const body = (
    <>
      <p className="text-sm text-muted">{label}</p>
      <p className="tnum mt-2 text-3xl font-semibold tracking-tight text-ink">{value}</p>
      <p className="mt-1 truncate text-sm text-faint">{sub}</p>
    </>
  )
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: index * 0.04, ease: 'easeOut' }}
      className="bg-surface"
    >
      {to ? (
        <Link to={to} className="block h-full px-5 py-4 hover:bg-subtle/60">
          {body}
        </Link>
      ) : (
        <div className="px-5 py-4">{body}</div>
      )}
    </motion.div>
  )
}

function Panel({ title, action, children, className = '' }) {
  return (
    <section className={`panel flex flex-col ${className}`}>
      <header className="flex items-center justify-between gap-3 border-b border-line px-5 py-3.5">
        <h2 className="text-md font-semibold text-ink">{title}</h2>
        {action}
      </header>
      <div className="flex-1 px-5 py-4">{children}</div>
    </section>
  )
}

const BAND_LABELS = { bench: 'Bench (0%)', light: 'Light (1–49%)', healthy: 'Healthy (50–89%)', full: 'Full (90–100%)' }

export default function Dashboard() {
  const { user, can } = useAuth()
  const [data, setData] = useState(null)
  const [starting, setStarting] = useState(false)
  const navigate = useNavigate()
  const toast = useToast()

  useEffect(() => {
    api
      .dashboard()
      .then(setData)
      .catch((e) => toast.error('Could not load the dashboard', e.detail))
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

  const c = data?.counts
  const m = data?.matching
  const tiles = c
    ? [
        { label: 'Candidates', value: c.candidates.toLocaleString(), sub: 'In the talent pool', to: '/candidates' },
        { label: 'Open jobs', value: c.jobs_open.toLocaleString(), sub: `${c.jobs_total} job specifications in total`, to: '/jobs' },
        { label: 'Applications in progress', value: c.applications_active.toLocaleString(), sub: `${c.hires_30_days} hired in the last 30 days`, to: '/pipeline' },
        {
          label: 'Staff utilisation',
          value: c.average_utilisation != null ? `${Math.round(c.average_utilisation)}%` : '–',
          sub: c.staff_active ? `${c.staff_active} active staff, ${c.staff_bench} on the bench` : 'No staff yet',
          to: '/resources',
        },
      ]
    : null

  const funnelRows = (data?.funnel || [])
    .filter((f) => f.stage !== 'rejected')
    .map((f) => ({
      key: f.stage,
      label: f.label,
      value: f.reached,
      note: f.conversion != null ? `${f.conversion}% of the previous stage · ${f.current} here now` : `${f.current} here now`,
    }))
  const rejected = data?.funnel?.find((f) => f.stage === 'rejected')?.current ?? 0

  return (
    <div className="space-y-8">
      <section className="flex flex-wrap items-end justify-between gap-6">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-ink">Dashboard</h1>
          <p className="mt-1 text-base text-muted">
            Signed in as {user.full_name} · {ROLE_LABELS[user.role]}
          </p>
        </div>
        {can('hiring:write') && (
          <div className="flex flex-wrap items-center gap-2">
            <button type="button" className="btn-secondary" onClick={startDemo} disabled={starting} data-testid="start-demo">
              {starting ? <Spinner /> : <PlayCircle size={16} aria-hidden />}
              Guided matching demo
            </button>
            <Link to="/jobs/new" className="btn-primary">
              <Plus size={16} aria-hidden /> New job
            </Link>
          </div>
        )}
        {!can('hiring:write') && can('resources:write') && (
          <Link to="/resources/projects" className="btn-primary">
            Manage projects <ArrowRight size={16} aria-hidden />
          </Link>
        )}
      </section>

      <section aria-label="Key figures" className="grid grid-cols-1 gap-px overflow-hidden rounded-lg border border-line bg-line sm:grid-cols-2 lg:grid-cols-4">
        {tiles
          ? tiles.map((t, i) => <Tile key={t.label} index={i} {...t} />)
          : [0, 1, 2, 3].map((i) => (
              <div key={i} className="bg-surface px-5 py-4">
                <Skeleton className="h-4 w-28" />
                <Skeleton className="mt-3 h-8 w-16" />
                <Skeleton className="mt-2 h-4 w-36" />
              </div>
            ))}
      </section>

      <div className="grid gap-6 lg:grid-cols-5">
        <Panel
          title="Hiring pipeline"
          className="lg:col-span-3"
          action={
            <Link to="/pipeline" className="flex items-center gap-1 text-sm font-medium text-accent hover:text-accent-hover">
              Open pipeline <ArrowRight size={14} aria-hidden />
            </Link>
          }
        >
          {data ? (
            data.counts.applications_active + rejected + (data.funnel[4]?.reached || 0) === 0 ? (
              <p className="py-8 text-center text-base text-muted">No applications yet. Add candidates to a job from the Matching screen.</p>
            ) : (
              <>
                <p className="mb-3 text-sm text-muted">Applications that reached each stage. Hover a bar for conversion.</p>
                <HBarChart rows={funnelRows} caption="Applications that reached each pipeline stage" valueLabel="Applications" />
                <p className="mt-3 text-sm text-faint">{rejected.toLocaleString()} rejected or withdrawn</p>
              </>
            )
          ) : (
            <Skeleton className="h-40 w-full" />
          )}
        </Panel>

        <Panel title="Staff by utilisation today" className="lg:col-span-2">
          {data ? (
            c.staff_active ? (
              <>
                <HBarChart
                  rows={Object.entries(data.utilisation_bands).map(([k, v]) => ({ key: k, label: BAND_LABELS[k], value: v }))}
                  caption="Active staff by utilisation band"
                  valueLabel="Staff"
                  onSelect={(r) => navigate(`/resources?band=${r.key}`)}
                />
                <p className="mt-3 text-sm text-faint">Select a band to see who is in it.</p>
              </>
            ) : (
              <p className="py-8 text-center text-base text-muted">No staff yet. People hired through the pipeline appear here.</p>
            )
          ) : (
            <Skeleton className="h-40 w-full" />
          )}
        </Panel>
      </div>

      <div className="grid gap-6 lg:grid-cols-5">
        <Panel title="Open jobs with the most applicants" className="lg:col-span-3">
          {data ? (
            data.applications_per_job.length ? (
              <HBarChart
                rows={data.applications_per_job.map((j) => ({ key: j.job_id, label: j.job_title, value: j.count, note: 'Open the pipeline for this job' }))}
                caption="Applications in progress per open job"
                valueLabel="Applications in progress"
                onSelect={(r) => navigate(`/pipeline/${r.key}`)}
              />
            ) : (
              <p className="py-8 text-center text-base text-muted">No applications in progress.</p>
            )
          ) : (
            <Skeleton className="h-40 w-full" />
          )}
        </Panel>

        <Panel title="Hires per month" className="lg:col-span-2">
          {data ? (
            <ColumnChart
              points={data.hires_per_month.map((h) => ({ key: h.month, label: h.label, value: h.count }))}
              caption="Hires per month, last six months"
              valueLabel="Hires"
            />
          ) : (
            <Skeleton className="h-40 w-full" />
          )}
        </Panel>
      </div>

      <div className="grid gap-6 lg:grid-cols-5">
        <Panel title="Recent pipeline activity" className="lg:col-span-3">
          {data ? (
            data.recent_activity.length ? (
              <ul className="-my-1 divide-y divide-line">
                {data.recent_activity.map((a) => (
                  <li key={a.event_id} className="flex items-baseline justify-between gap-4 py-2.5">
                    <p className="min-w-0 text-base text-ink">
                      <span className="font-medium">{a.candidate_name}</span>
                      <span className="text-muted">
                        {a.from_stage ? ' moved to ' : ' applied for '}
                        {a.from_stage && <span className="font-medium text-ink">{STAGE_LABELS[a.to_stage]}</span>}
                        {a.from_stage ? ' · ' : ''}
                        {a.job_title}
                      </span>
                    </p>
                    <span className="shrink-0 text-sm text-faint" title={a.changed_by || ''}>
                      {timeAgo(a.changed_at)}
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="py-8 text-center text-base text-muted">Nothing has happened yet.</p>
            )
          ) : (
            <Skeleton className="h-40 w-full" />
          )}
        </Panel>

        <Panel title="Matching engine" className="lg:col-span-2">
          {m ? (
            <dl className="space-y-3 text-base">
              <div className="flex justify-between gap-4">
                <dt className="text-muted">Last run</dt>
                <dd className="text-right text-ink">{m.last_run_at ? capitalise(timeAgo(m.last_run_at)) : 'Never'}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-muted">Job</dt>
                <dd className="truncate text-right text-ink">
                  {m.last_run_job_id && can('results:view') ? (
                    <Link className="text-accent hover:text-accent-hover" to={`/results/${m.last_run_job_id}`}>
                      {m.last_run_job_title}
                    </Link>
                  ) : (
                    m.last_run_job_title || '–'
                  )}
                </dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-muted">Average score</dt>
                <dd className="tnum text-ink">{m.average_score != null ? `${m.average_score.toFixed(1)} / 100` : '–'}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-muted">Language model</dt>
                <dd className="text-right text-ink">
                  {m.embedder.includes('MiniLM')
                    ? 'all-MiniLM-L6-v2 (local)'
                    : m.embedder === 'not-loaded'
                      ? 'Loads on first match'
                      : 'Fallback (model not downloaded)'}
                </dd>
              </div>
              <p className="border-t border-line pt-3 text-sm text-faint">
                Scores combine skills, experience, education and how closely the CV describes the job. Names, age and gender are never used.
              </p>
            </dl>
          ) : (
            <Skeleton className="h-40 w-full" />
          )}
        </Panel>
      </div>
    </div>
  )
}
