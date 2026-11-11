import { KanbanSquare, Plus, RotateCcw, Search, UserPlus, X } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../apiClient'
import { SlideOver } from '../components/Overlay'
import { useToast } from '../components/Toast'
import { EmptyState, Field, PageHeader, Skeleton, Spinner } from '../components/ui'
import { useAuth } from '../lib/auth'
import { dateTime, timeAgo, years } from '../lib/format'
import { useDebounced } from '../lib/hooks'
import { FLOW, STAGES, STAGE_LABELS, groupByStage, moveLabel } from '../lib/stages'

const COLUMN_LIMIT = 30

/** Small stage marker: a filled dot for the stage's position in the flow. */
function StageSteps({ stage }) {
  const at = FLOW.indexOf(stage)
  return (
    <span className="flex items-center gap-0.5" aria-hidden>
      {FLOW.map((s, i) => (
        <span
          key={s}
          className={`h-1 w-3 rounded-full ${stage === 'rejected' ? 'bg-line-strong' : i <= at ? 'bg-accent' : 'bg-bar-track'}`}
        />
      ))}
    </span>
  )
}

function Card({ app, showJob, onOpen }) {
  return (
    <li>
      <button
        type="button"
        onClick={onOpen}
        className="w-full rounded-md border border-line bg-surface px-3 py-2.5 text-left shadow-[0_1px_1px_rgb(15_23_42/0.04)] hover:border-line-strong"
        data-testid="pipeline-card"
      >
        <div className="flex items-start justify-between gap-2">
          <span className="min-w-0 truncate text-base font-medium text-ink">{app.candidate_name}</span>
          {app.match_score != null && (
            <span className="tnum shrink-0 text-sm font-medium text-muted" title="Match score when added">
              {app.match_score.toFixed(0)}
            </span>
          )}
        </div>
        <p className="truncate text-sm text-faint">{showJob ? app.job_title : app.candidate_titles || years(app.years_experience)}</p>
        <p className="mt-1.5 text-xs text-faint">Updated {timeAgo(app.updated_at)}</p>
      </button>
    </li>
  )
}

function Column({ stage, apps, showJob, onOpen }) {
  const [all, setAll] = useState(false)
  const shown = all ? apps : apps.slice(0, COLUMN_LIMIT)
  return (
    <section className="flex min-w-[12rem] flex-1 flex-col rounded-lg bg-subtle/70" aria-label={`${STAGE_LABELS[stage]}: ${apps.length}`}>
      <header className="flex items-center justify-between px-3 pb-2 pt-3">
        <h2 className="text-sm font-semibold text-ink">{STAGE_LABELS[stage]}</h2>
        <span className="tnum rounded bg-surface px-1.5 text-xs font-medium text-muted">{apps.length}</span>
      </header>
      <ul className="flex-1 space-y-2 overflow-y-auto px-2 pb-2" style={{ maxHeight: 'calc(100vh - 17rem)' }}>
        {shown.map((a) => (
          <Card key={a.application_id} app={a} showJob={showJob} onOpen={() => onOpen(a.application_id)} />
        ))}
        {apps.length === 0 && <li className="px-1 py-6 text-center text-sm text-faint">None</li>}
        {apps.length > shown.length && (
          <li>
            <button type="button" className="btn-ghost btn-sm w-full" onClick={() => setAll(true)}>
              Show all {apps.length}
            </button>
          </li>
        )}
      </ul>
    </section>
  )
}

function Detail({ appId, onClose, onChanged }) {
  const { can } = useAuth()
  const toast = useToast()
  const [app, setApp] = useState(null)
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    setApp(null)
    setNote('')
    setError(null)
    if (!appId) return
    api
      .getApplication(appId)
      .then(setApp)
      .catch((e) => toast.error('Could not open the application', e.detail))
  }, [appId, toast])

  const move = async (stage) => {
    setBusy(stage)
    setError(null)
    try {
      const updated = await api.moveApplication(app.application_id, stage, note.trim() || null)
      setApp(updated)
      setNote('')
      onChanged(updated)
      toast.success(`${updated.candidate_name}: ${STAGE_LABELS[stage]}`, stage === 'hired' ? 'Added to the staff pool for project allocation.' : undefined)
    } catch (e) {
      setError(e.detail)
    } finally {
      setBusy(null)
    }
  }

  const forward = app?.allowed_moves.filter((s) => s !== 'rejected') || []
  const canReject = app?.allowed_moves.includes('rejected')

  return (
    <SlideOver
      open={Boolean(appId)}
      onClose={onClose}
      title={app ? app.candidate_name : 'Application'}
      subtitle={app ? `${app.job_title} · ${STAGE_LABELS[app.stage]}` : ''}
      width="w-[32rem]"
      footer={
        app &&
        can('hiring:write') &&
        app.allowed_moves.length > 0 && (
          <div className="flex w-full flex-wrap items-center gap-2">
            {forward.map((s) => (
              <button key={s} type="button" className={s === 'hired' ? 'btn-go' : 'btn-primary'} disabled={busy !== null} onClick={() => move(s)}>
                {busy === s ? <Spinner /> : app.stage === 'rejected' ? <RotateCcw size={15} aria-hidden /> : null}
                {app.stage === 'rejected' ? `Reopen at ${STAGE_LABELS[s]}` : moveLabel(s)}
              </button>
            ))}
            {canReject && (
              <button type="button" className="btn-danger-ghost ml-auto" disabled={busy !== null} onClick={() => move('rejected')}>
                {busy === 'rejected' ? <Spinner /> : <X size={15} aria-hidden />} Reject
              </button>
            )}
          </div>
        )
      }
    >
      {!app ? (
        <div className="space-y-3">
          <Skeleton className="h-6 w-1/2" />
          <Skeleton className="h-24 w-full" />
        </div>
      ) : (
        <div className="space-y-6">
          <div className="flex items-center justify-between gap-4 rounded-lg border border-line bg-canvas px-4 py-3">
            <div>
              <p className="text-sm text-muted">Current stage</p>
              <p className="text-lg font-semibold text-ink">{STAGE_LABELS[app.stage]}</p>
            </div>
            <StageSteps stage={app.stage} />
          </div>

          <dl className="grid grid-cols-2 gap-x-6 gap-y-3 text-base">
            <div>
              <dt className="text-sm text-muted">Experience</dt>
              <dd className="text-ink">{years(app.years_experience)}</dd>
            </div>
            <div>
              <dt className="text-sm text-muted">Location</dt>
              <dd className="text-ink">{app.candidate_location || '–'}</dd>
            </div>
            <div>
              <dt className="text-sm text-muted">Match score when added</dt>
              <dd className="tnum text-ink">{app.match_score != null ? `${app.match_score.toFixed(1)} / 100` : 'Not from a match run'}</dd>
            </div>
            <div>
              <dt className="text-sm text-muted">Applied</dt>
              <dd className="text-ink">{dateTime(app.applied_at)}</dd>
            </div>
            {app.candidate_titles && (
              <div className="col-span-2">
                <dt className="text-sm text-muted">Previous titles</dt>
                <dd className="text-ink">{app.candidate_titles}</dd>
              </div>
            )}
          </dl>

          {can('hiring:write') && app.allowed_moves.length > 0 && (
            <Field label="Note for the next change" optional hint="Saved in the history with your name, for example the reason for a rejection.">
              {({ id, describedBy }) => (
                <textarea id={id} rows={2} maxLength={500} className="input" value={note} onChange={(e) => setNote(e.target.value)} aria-describedby={describedBy} />
              )}
            </Field>
          )}
          {error && (
            <p role="alert" className="rounded border border-danger/30 bg-danger-soft px-3 py-2 text-sm text-danger">
              {error}
            </p>
          )}
          {app.stage === 'hired' && (
            <p className="rounded border border-go/30 bg-go-soft px-3 py-2 text-sm text-ink">
              Hired. {app.candidate_name} is in the staff pool.{' '}
              <Link to="/resources" className="font-medium text-accent hover:underline">
                Allocate to a project
              </Link>
            </p>
          )}

          <section>
            <h3 className="mb-3 text-sm font-semibold text-ink">History</h3>
            <ol className="relative space-y-4 border-l border-line pl-5">
              {[...app.events].reverse().map((e) => (
                <li key={e.event_id} className="relative">
                  <span
                    className={`absolute -left-[1.6rem] top-1.5 h-2.5 w-2.5 rounded-full border-2 border-surface ${
                      e.to_stage === 'rejected' ? 'bg-faint' : 'bg-accent'
                    }`}
                    aria-hidden
                  />
                  <p className="text-base text-ink">
                    {e.from_stage ? (
                      <>
                        {STAGE_LABELS[e.from_stage]} <span className="text-faint">to</span> <span className="font-medium">{STAGE_LABELS[e.to_stage]}</span>
                      </>
                    ) : (
                      <span className="font-medium">Applied</span>
                    )}
                  </p>
                  <p className="text-sm text-faint">
                    {dateTime(e.changed_at)}
                    {e.changed_by_name ? ` · ${e.changed_by_name}` : ''}
                  </p>
                  {e.note && <p className="mt-1 text-sm text-muted">{e.note}</p>}
                </li>
              ))}
            </ol>
          </section>
        </div>
      )}
    </SlideOver>
  )
}

function AddCandidate({ open, job, onClose, onAdded, existing }) {
  const toast = useToast()
  const [all, setAll] = useState(null)
  const [q, setQ] = useState('')
  const [busy, setBusy] = useState(null)
  const dq = useDebounced(q, 120)
  useEffect(() => {
    if (!open) return
    setQ('')
    if (!all) api.listCandidates().then((r) => setAll(r.items)).catch(() => setAll([]))
  }, [open, all])
  const list = useMemo(() => {
    if (!all) return []
    const t = dq.trim().toLowerCase()
    return all
      .filter((c) => !existing.has(c.candidate_id))
      .filter((c) => !t || c.full_name.toLowerCase().includes(t) || (c.previous_titles || '').toLowerCase().includes(t))
      .slice(0, 50)
  }, [all, dq, existing])

  const add = async (c) => {
    setBusy(c.candidate_id)
    try {
      const app = await api.createApplication({ candidate_id: c.candidate_id, job_id: job.job_id })
      toast.success(`${c.full_name} added`, `Applied for ${job.job_title}`)
      onAdded(app)
    } catch (e) {
      toast.error('Could not add the candidate', e.detail)
    } finally {
      setBusy(null)
    }
  }

  return (
    <SlideOver open={open} onClose={onClose} title="Add a candidate" subtitle={job ? job.job_title : ''} width="w-[30rem]">
      <div className="relative mb-3">
        <Search size={15} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-faint" aria-hidden />
        <input
          type="search"
          className="input pl-9"
          placeholder="Search by name or title"
          aria-label="Search candidates"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
      </div>
      <p className="mb-2 text-sm text-faint">
        Tip: to add the best fits, run a match on the{' '}
        <Link className="text-accent hover:underline" to={job ? `/results/${job.job_id}` : '/results'}>
          Matching
        </Link>{' '}
        screen and add from the ranked list.
      </p>
      {all === null ? (
        <Skeleton className="h-40 w-full" />
      ) : (
        <ul className="divide-y divide-line rounded-lg border border-line">
          {list.map((c) => (
            <li key={c.candidate_id} className="flex items-center justify-between gap-3 px-3 py-2">
              <div className="min-w-0">
                <p className="truncate text-base font-medium text-ink">{c.full_name}</p>
                <p className="truncate text-sm text-faint">{c.previous_titles || years(c.years_experience)}</p>
              </div>
              <button type="button" className="btn-secondary btn-sm shrink-0" onClick={() => add(c)} disabled={busy !== null}>
                {busy === c.candidate_id ? <Spinner /> : <Plus size={14} aria-hidden />} Add
              </button>
            </li>
          ))}
          {list.length === 0 && <li className="px-3 py-6 text-center text-sm text-muted">No matching candidates.</li>}
        </ul>
      )}
    </SlideOver>
  )
}

export default function Pipeline() {
  const { jobId } = useParams()
  const navigate = useNavigate()
  const toast = useToast()
  const { can } = useAuth()
  const [jobs, setJobs] = useState(null)
  const [apps, setApps] = useState(null)
  const [query, setQuery] = useState('')
  const [openId, setOpenId] = useState(null)
  const [adding, setAdding] = useState(false)
  const dq = useDebounced(query, 150)
  const id = jobId ? Number(jobId) : null
  const job = jobs?.find((j) => j.job_id === id) || null

  useEffect(() => {
    api.listJobs().then(setJobs).catch(() => setJobs([]))
  }, [])

  const load = useCallback(() => {
    setApps(null)
    api
      .listApplications(id ? { job_id: id } : {})
      .then(setApps)
      .catch((e) => {
        setApps([])
        toast.error('Could not load the pipeline', e.detail)
      })
  }, [id, toast])
  useEffect(load, [load])

  const filtered = useMemo(() => {
    if (!apps) return []
    const t = dq.trim().toLowerCase()
    if (!t) return apps
    return apps.filter((a) => a.candidate_name.toLowerCase().includes(t) || a.job_title.toLowerCase().includes(t))
  }, [apps, dq])
  const columns = useMemo(() => groupByStage(filtered), [filtered])
  const existing = useMemo(() => new Set((apps || []).map((a) => a.candidate_id)), [apps])

  const onChanged = (updated) =>
    setApps((list) => list.map((a) => (a.application_id === updated.application_id ? { ...a, ...updated, events: undefined } : a)))

  return (
    <div>
      <PageHeader
        title="Applicant pipeline"
        description={
          apps
            ? `${filtered.length.toLocaleString()} application${filtered.length === 1 ? '' : 's'}${job ? ` for ${job.job_title}` : ' across all jobs'}`
            : 'Loading applications'
        }
        actions={
          can('hiring:write') &&
          job && (
            <button type="button" className="btn-primary" onClick={() => setAdding(true)} disabled={job.status === 'closed'} title={job.status === 'closed' ? 'This job is closed' : undefined}>
              <UserPlus size={16} aria-hidden /> Add candidate
            </button>
          )
        }
      />

      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div className="relative">
          <select
            className="input w-72 pr-8"
            aria-label="Job"
            value={id || ''}
            onChange={(e) => navigate(e.target.value ? `/pipeline/${e.target.value}` : '/pipeline')}
          >
            <option value="">All jobs</option>
            {(jobs || []).map((j) => (
              <option key={j.job_id} value={j.job_id}>
                {j.job_title}
                {j.status === 'closed' ? ' (closed)' : ''}
              </option>
            ))}
          </select>
        </div>
        <div className="relative w-full max-w-xs">
          <Search size={15} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-faint" aria-hidden />
          <input
            type="search"
            className="input pl-9"
            placeholder={job ? 'Find a candidate' : 'Find a candidate or job'}
            aria-label="Filter applications"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
        {job && (
          <span className="text-sm text-muted">
            {job.location} · {job.status === 'closed' ? 'Closed' : 'Open'}
          </span>
        )}
      </div>

      {apps === null ? (
        <div className="flex gap-3">
          {STAGES.map((s) => (
            <Skeleton key={s} className="h-80 min-w-[12rem] flex-1" />
          ))}
        </div>
      ) : apps.length === 0 ? (
        <div className="panel">
          <EmptyState
            icon={KanbanSquare}
            title={job ? 'Nobody has applied yet' : 'No applications yet'}
            action={
              can('hiring:write') &&
              (job ? (
                <button type="button" className="btn-primary" onClick={() => setAdding(true)}>
                  <UserPlus size={16} aria-hidden /> Add candidate
                </button>
              ) : (
                <Link to="/results" className="btn-primary">
                  Go to Matching
                </Link>
              ))
            }
          >
            Add candidates from the Matching screen, where they are ranked against the job, or add them one by one.
          </EmptyState>
        </div>
      ) : (
        <div className="-mx-1 overflow-x-auto px-1 pb-2">
          <div className="flex gap-3" data-testid="pipeline-board">
            {STAGES.map((s) => (
              <Column key={`${id}-${s}`} stage={s} apps={columns[s] || []} showJob={!job} onOpen={setOpenId} />
            ))}
          </div>
        </div>
      )}

      <Detail appId={openId} onClose={() => setOpenId(null)} onChanged={onChanged} />
      <AddCandidate
        open={adding}
        job={job}
        existing={existing}
        onClose={() => setAdding(false)}
        onAdded={(app) => {
          setApps((list) => [app, ...(list || [])])
          setAdding(false)
        }}
      />
    </div>
  )
}
