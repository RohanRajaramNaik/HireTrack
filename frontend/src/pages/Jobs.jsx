import { motion } from 'framer-motion'
import { KanbanSquare, PlayCircle, Plus, Save, Search, Trash2, Zap } from 'lucide-react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import { api } from '../apiClient'
import { ConfirmDialog } from '../components/Overlay'
import TagInput from '../components/TagInput'
import { useToast } from '../components/Toast'
import WeightSliders from '../components/WeightSliders'
import { Field, Skeleton, Spinner } from '../components/ui'
import { useAuth } from '../lib/auth'
import { skillLabel, timeAgo } from '../lib/format'
import { useEducationLevels } from '../lib/hooks'
import { DEFAULT_WEIGHTS, toWeightFields, weightTotal, weightsOf } from '../lib/scoring'
import { validateJob } from '../lib/validation'

const BLANK = {
  job_title: '',
  created_by: '',
  location: '',
  status: 'open',
  min_experience: 0,
  min_level_id: '4',
  job_description: '',
  required_skills: [],
  preferred_skills: [],
  weights: { ...DEFAULT_WEIGHTS },
}

const fromJob = (j) => ({
  job_title: j.job_title,
  created_by: j.created_by || '',
  location: j.location || '',
  status: j.status || 'open',
  min_experience: j.min_experience,
  min_level_id: String(j.min_level_id),
  job_description: j.job_description,
  required_skills: j.required_skills.map(skillLabel),
  preferred_skills: j.preferred_skills.map(skillLabel),
  weights: weightsOf(j),
})

const toBody = (v) => ({
  job_title: v.job_title.trim(),
  created_by: v.created_by.trim() || null,
  location: v.location.trim(),
  status: v.status,
  min_experience: Number(v.min_experience),
  min_level_id: Number(v.min_level_id),
  job_description: v.job_description.trim(),
  required_skills: v.required_skills,
  preferred_skills: v.preferred_skills,
  ...toWeightFields(v.weights),
})

function Section({ title, description, children }) {
  return (
    <section className="grid gap-6 border-b border-line px-6 py-6 last:border-b-0 lg:grid-cols-[14rem_minmax(0,1fr)]">
      <div>
        <h2 className="text-md font-semibold text-ink">{title}</h2>
        {description && <p className="mt-1 text-sm text-muted">{description}</p>}
      </div>
      <div className="min-w-0 space-y-5">{children}</div>
    </section>
  )
}

export default function Jobs() {
  const { user, can } = useAuth()
  const canEdit = can('hiring:write')
  const canMatch = can('results:view')
  const [filter, setFilter] = useState('')
  const { jobId } = useParams()
  const location = useLocation()
  const navigate = useNavigate()
  const toast = useToast()
  const levels = useEducationLevels()
  const [jobs, setJobs] = useState(null)
  const [v, setV] = useState(BLANK)
  const [saved, setSaved] = useState(BLANK)
  const [loadingJob, setLoadingJob] = useState(false)
  const [errors, setErrors] = useState({})
  const [submitted, setSubmitted] = useState(false)
  const [busy, setBusy] = useState(null) // 'save' | 'run' | null
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [slowRun, setSlowRun] = useState(false)
  const demo = Boolean(location.state?.demo)

  // A first match on newly loaded candidates reads every CV once (about 10 s
  // per 1,000 on a laptop CPU). Explain the wait instead of leaving a spinner.
  useEffect(() => {
    if (busy !== 'run') {
      setSlowRun(false)
      return undefined
    }
    const t = setTimeout(() => setSlowRun(true), 1500)
    return () => clearTimeout(t)
  }, [busy])
  const demoFired = useRef(false)

  const isNew = jobId === 'new' || (!jobId && jobs && jobs.length === 0)
  const currentId = jobId && jobId !== 'new' ? Number(jobId) : null

  const refreshJobs = useCallback(() => api.listJobs().then(setJobs).catch(() => setJobs([])), [])
  useEffect(() => {
    refreshJobs()
  }, [refreshJobs])

  // /jobs with no id: open the most recent job (or a blank form if none).
  useEffect(() => {
    if (!jobId && jobs && jobs.length) navigate(`/jobs/${jobs[0].job_id}`, { replace: true })
  }, [jobId, jobs, navigate])

  useEffect(() => {
    setErrors({})
    setSubmitted(false)
    if (!currentId) {
      const blank = { ...BLANK, created_by: user.full_name }
      setV(blank)
      setSaved(blank)
      return
    }
    setLoadingJob(true)
    api
      .getJob(currentId)
      .then((j) => {
        const f = fromJob(j)
        setV(f)
        setSaved(f)
      })
      .catch((e) => toast.error('Could not load job', e.detail))
      .finally(() => setLoadingJob(false))
  }, [currentId, toast])

  const dirty = useMemo(() => JSON.stringify(v) !== JSON.stringify(saved), [v, saved])
  const total = weightTotal(v.weights)
  const liveErrors = useMemo(() => validateJob(v), [v])
  const canRun = total === 100 && Object.keys(liveErrors).length === 0

  const update = (patch) => {
    const next = { ...v, ...patch }
    setV(next)
    if (submitted) setErrors(validateJob(next))
    else if (patch.weights) setErrors((e) => ({ ...e, weights: validateJob(next).weights }))
  }
  const set = (k) => (e) => update({ [k]: e && e.target ? e.target.value : e })

  const save = async () => {
    setSubmitted(true)
    const errs = validateJob(v)
    setErrors(errs)
    if (Object.keys(errs).length) {
      setTimeout(() => document.querySelector('[aria-invalid="true"]')?.focus(), 0)
      return null
    }
    try {
      const job = currentId ? await api.updateJob(currentId, toBody(v)) : await api.createJob(toBody(v))
      const f = fromJob(job)
      setV(f)
      setSaved(f)
      refreshJobs()
      return job
    } catch (err) {
      if (err.field) setErrors({ [err.field]: err.detail })
      else toast.error('Could not save job', err.detail)
      return null
    }
  }

  const onSave = async () => {
    setBusy('save')
    const job = await save()
    setBusy(null)
    if (job) {
      toast.success('Job saved', job.job_title)
      if (!currentId) navigate(`/jobs/${job.job_id}`, { replace: true })
    }
  }

  const onRun = async () => {
    setBusy('run')
    let id = currentId
    if (!id || dirty) {
      const job = await save()
      if (!job) {
        setBusy(null)
        return
      }
      id = job.job_id
    }
    try {
      const results = await api.runMatch(id)
      navigate(`/results/${id}`, { state: { fresh: results, tour: demo } })
    } catch (e) {
      toast.error('Match could not run', e.detail)
      setBusy(null)
    }
  }

  // Guided demo: the job arrives pre-filled; run the match automatically.
  useEffect(() => {
    if (demo && !demoFired.current && currentId && !loadingJob && saved.job_title) {
      demoFired.current = true
      const t = setTimeout(onRun, 1400)
      return () => clearTimeout(t)
    }
    return undefined
  }, [demo, currentId, loadingJob, saved.job_title]) // eslint-disable-line react-hooks/exhaustive-deps

  const onDelete = async () => {
    try {
      await api.deleteJob(currentId)
      toast.success('Job deleted', saved.job_title)
      setConfirmDelete(false)
      const rest = (jobs || []).filter((j) => j.job_id !== currentId)
      setJobs(rest)
      navigate(rest.length ? `/jobs/${rest[0].job_id}` : '/jobs/new', { replace: true })
    } catch (e) {
      toast.error('Could not delete job', e.detail)
    }
  }

  const currentMeta = jobs?.find((j) => j.job_id === currentId)

  return (
    <div className="grid gap-6 lg:grid-cols-[17rem_minmax(0,1fr)]">
      <aside className="lg:sticky lg:top-20 lg:self-start">
        <div className="mb-3 flex items-center justify-between">
          <h1 className="text-lg font-semibold tracking-tight text-ink">Job specifications</h1>
        </div>
        {canEdit && (
          <Link to="/jobs/new" className="btn-secondary mb-3 w-full">
            <Plus size={16} aria-hidden /> New job
          </Link>
        )}
        {jobs && jobs.length > 6 && (
          <div className="relative mb-2">
            <Search size={14} className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-faint" aria-hidden />
            <input
              type="search"
              className="input h-8 pl-8 text-sm"
              placeholder="Filter jobs"
              aria-label="Filter jobs"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
            />
          </div>
        )}
        <nav aria-label="Saved jobs" className="max-h-[calc(100vh-14rem)] space-y-0.5 overflow-y-auto pr-1">
          {jobs === null
            ? [0, 1, 2].map((i) => <Skeleton key={i} className="h-12 w-full" />)
            : jobs
                .filter((j) => {
                  const q = filter.trim().toLowerCase()
                  return !q || j.job_title.toLowerCase().includes(q) || j.location.toLowerCase().includes(q)
                })
                .map((j) => {
                const active = j.job_id === currentId
                return (
                  <Link
                    key={j.job_id}
                    to={`/jobs/${j.job_id}`}
                    className={`relative block rounded px-3 py-2 ${active ? 'bg-surface ring-1 ring-line' : 'hover:bg-subtle'}`}
                    aria-current={active ? 'page' : undefined}
                  >
                    {active && <span className="absolute inset-y-2 left-0 w-0.5 rounded-full bg-accent" aria-hidden />}
                    <span className="block truncate text-base font-medium text-ink">{j.job_title}</span>
                    <span className="block truncate text-xs text-faint">
                      {j.status === 'closed' ? 'Closed · ' : ''}
                      {j.location} · {j.last_run_at ? `matched ${timeAgo(j.last_run_at)}` : 'not matched yet'}
                    </span>
                  </Link>
                )
              })}
          {jobs && jobs.length === 0 && <p className="px-3 py-2 text-sm text-muted">No saved jobs yet. Fill in the form to create your first one.</p>}
        </nav>
      </aside>

      <div className="min-w-0">
        {demo && (
          <motion.div
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-4 flex items-center gap-3 rounded-lg border border-accent/30 bg-accent-soft px-4 py-3 text-base text-accent-ink"
            role="status"
          >
            <PlayCircle size={18} aria-hidden />
            <span>
              <strong className="font-semibold">Guided demo.</strong> This Cloud Data Engineer specification is filled in. Matching it against every candidate now…
            </span>
            <Spinner />
          </motion.div>
        )}

        <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
          <div className="min-w-0">
            <p className="text-sm text-faint">{isNew ? 'New job specification' : canEdit ? 'Editing job specification' : 'Job specification (read only)'}</p>
            <h2 className="truncate text-2xl font-semibold tracking-tight text-ink">{v.job_title.trim() || 'Untitled job'}</h2>
          </div>
          <div className="flex flex-wrap items-center gap-4">
            {currentId && (
              <Link to={`/pipeline/${currentId}`} className="inline-flex items-center gap-1.5 text-sm font-medium text-accent hover:underline">
                <KanbanSquare size={14} aria-hidden /> Pipeline for this job
              </Link>
            )}
            {canMatch && currentMeta?.last_run_at && (
              <Link to={`/results/${currentId}`} className="text-sm font-medium text-accent hover:underline">
                View last results ({timeAgo(currentMeta.last_run_at)})
              </Link>
            )}
          </div>
        </div>

        <form
          className="panel"
          noValidate
          onSubmit={(e) => {
            e.preventDefault()
            onSave()
          }}
        >
          {loadingJob ? (
            <div className="space-y-4 p-6">
              {[0, 1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : (
            <fieldset disabled={!canEdit} className="min-w-0">
              <Section title="Role" description="The basics a candidate must meet.">
                <Field label="Job title" error={errors.job_title}>
                  {({ id, invalid, describedBy }) => (
                    <input id={id} className="input" value={v.job_title} onChange={set('job_title')} aria-invalid={invalid} aria-describedby={describedBy} maxLength={120} placeholder="e.g. Cloud Data Engineer" />
                  )}
                </Field>
                <div className="grid gap-4 sm:grid-cols-3">
                  <Field label="Minimum years" error={errors.min_experience}>
                    {({ id, invalid, describedBy }) => (
                      <input id={id} type="number" min={0} max={50} step={0.5} className="input tnum" value={v.min_experience} onChange={set('min_experience')} aria-invalid={invalid} aria-describedby={describedBy} />
                    )}
                  </Field>
                  <Field label="Minimum education" error={errors.min_level_id}>
                    {({ id, invalid, describedBy }) => (
                      <select id={id} className="input" value={v.min_level_id} onChange={set('min_level_id')} aria-invalid={invalid} aria-describedby={describedBy}>
                        <option value="">Choose a level</option>
                        {levels.map((l) => (
                          <option key={l.level_id} value={l.level_id}>
                            {l.level_name}
                          </option>
                        ))}
                      </select>
                    )}
                  </Field>
                  <Field label="Created by" optional>
                    {({ id }) => <input id={id} className="input" value={v.created_by} onChange={set('created_by')} maxLength={100} />}
                  </Field>
                </div>
                <div className="grid gap-4 sm:grid-cols-3">
                  <Field label="Location" error={errors.location} className="sm:col-span-2">
                    {({ id, invalid, describedBy }) => (
                      <input id={id} className="input" value={v.location} onChange={set('location')} aria-invalid={invalid} aria-describedby={describedBy} maxLength={80} placeholder="e.g. Johannesburg, or Remote" />
                    )}
                  </Field>
                  <Field label="Status" hint="Closed jobs accept no new applicants.">
                    {({ id, describedBy }) => (
                      <select id={id} className="input" value={v.status} onChange={set('status')} aria-describedby={describedBy}>
                        <option value="open">Open</option>
                        <option value="closed">Closed</option>
                      </select>
                    )}
                  </Field>
                </div>
              </Section>

              <Section title="Skills" description="Required skills carry 80% of the skills score, preferred skills 20%.">
                <Field label="Required skills" error={errors.required_skills} hint="At least one. Press Enter after each skill.">
                  {({ id, invalid, describedBy }) => (
                    <TagInput id={id} label="Required skills" tone="required" value={v.required_skills} onChange={set('required_skills')} invalid={invalid} describedBy={describedBy} />
                  )}
                </Field>
                <Field label="Preferred skills" optional error={errors.preferred_skills} hint="Nice to have. Must not repeat a required skill.">
                  {({ id, invalid, describedBy }) => (
                    <TagInput id={id} label="Preferred skills" value={v.preferred_skills} onChange={set('preferred_skills')} invalid={invalid} describedBy={describedBy} />
                  )}
                </Field>
              </Section>

              <Section title="Description" description="Compared with each CV summary to find people who describe the same work in other words.">
                <Field label="Job description" error={errors.job_description} count={v.job_description.trim().length} max={5000}>
                  {({ id, invalid, describedBy }) => (
                    <textarea id={id} rows={7} className="input" value={v.job_description} onChange={set('job_description')} aria-invalid={invalid} aria-describedby={describedBy} />
                  )}
                </Field>
              </Section>

              <Section title="Scoring weights" description="How much each part counts towards the overall score. Must total exactly 100%.">
                <WeightSliders
                  idPrefix="job"
                  weights={v.weights}
                  onChange={(w) => update({ weights: w })}
                  onReset={() => update({ weights: { ...DEFAULT_WEIGHTS } })}
                />
                {errors.weights && (
                  <p role="alert" className="text-sm text-danger">
                    {errors.weights}
                  </p>
                )}
              </Section>
            </fieldset>
          )}

          {canEdit && (
          <div className="sticky bottom-0 flex flex-wrap items-center gap-2 rounded-b-lg border-t border-line bg-surface/95 px-6 py-3 backdrop-blur-[2px]">
            {currentId && (
              <button type="button" className="btn-danger-ghost -ml-2" onClick={() => setConfirmDelete(true)}>
                <Trash2 size={15} aria-hidden /> Delete job
              </button>
            )}
            <span className="ml-auto text-sm text-faint" aria-live="polite">
              {dirty ? 'Unsaved changes' : currentId ? 'All changes saved' : ''}
            </span>
            <button type="submit" className="btn-secondary" disabled={busy !== null}>
              {busy === 'save' ? <Spinner /> : <Save size={15} aria-hidden />}
              Save job
            </button>
            <button
              type="button"
              className="btn-go"
              onClick={onRun}
              disabled={!canRun || busy !== null}
              title={total !== 100 ? `Weights must add up to 100% (now ${total}%)` : !canRun ? 'Complete the required fields first' : undefined}
              data-testid="run-match"
            >
              {busy === 'run' ? <Spinner /> : <Zap size={15} aria-hidden />}
              {busy === 'run' ? 'Matching…' : 'Run Match'}
            </button>
          </div>
          )}
        </form>
        {slowRun && (
          <p className="mt-2 text-right text-sm text-muted" role="status">
            Reading new CVs for the first time. This takes about 10 seconds per 1,000 candidates and only happens once.
          </p>
        )}
        {canEdit && !canRun && total !== 100 && (
          <p className="mt-2 text-right text-sm text-warn">Run Match unlocks when the weights total exactly 100% (now {total}%).</p>
        )}
      </div>

      <ConfirmDialog
        open={confirmDelete}
        title={`Delete “${saved.job_title}”?`}
        confirmLabel="Delete job"
        onConfirm={onDelete}
        onCancel={() => setConfirmDelete(false)}
      >
        The job specification and all of its match results will be permanently removed.
      </ConfirmDialog>
    </div>
  )
}

