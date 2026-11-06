import { AnimatePresence, LayoutGroup, motion } from 'framer-motion'
import {
  ArrowDown,
  ArrowUp,
  Check,
  ChevronDown,
  ChevronRight,
  Columns3,
  Download,
  MessageSquareText,
  SearchX,
  SlidersHorizontal,
  Trophy,
  X,
  Zap,
} from 'lucide-react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import { api } from '../apiClient'
import AnimatedNumber from '../components/AnimatedNumber'
import MetricBar from '../components/MetricBar'
import { SlideOver } from '../components/Overlay'
import RadarChart, { SERIES_STYLES } from '../components/RadarChart'
import Tour from '../components/Tour'
import { useToast } from '../components/Toast'
import WeightSliders from '../components/WeightSliders'
import { EmptyState, Skeleton, Spinner } from '../components/ui'
import { duration, skillLabel, timeAgo, years } from '../lib/format'
import { demoState } from '../lib/hooks'
import { METRICS, calculation, rerank, sameWeights, weightsOf } from '../lib/scoring'

const PAGE = 50
const GRID = 'grid grid-cols-[1.75rem_2.75rem_minmax(11rem,1.3fr)_5.5rem_repeat(4,minmax(6.5rem,1fr))_1.25rem] items-center gap-x-5'
const STAGGER = 0.06

/* ------------------------------------------------------------------ skills */
function SkillGroup({ title, matched, missing, aliases }) {
  const total = matched.length + missing.length
  if (!total) return null
  return (
    <div>
      <div className="mb-2 flex items-baseline justify-between">
        <h4 className="text-sm font-medium text-ink">{title}</h4>
        <span className="tnum text-sm text-muted">
          {matched.length} of {total} matched
        </span>
      </div>
      <ul className="flex flex-wrap gap-1.5" aria-label={`${title}`}>
        {matched.map((s) => (
          <li key={s} className="chip-match">
            <Check size={12} aria-hidden />
            <span className="sr-only">Has </span>
            {skillLabel(s)}
            {aliases[s] && <span className="font-normal text-accent-ink/70">· listed as “{aliases[s]}”</span>}
          </li>
        ))}
        {missing.map((s) => (
          <li key={s} className="chip-missing">
            <X size={12} aria-hidden />
            <span className="sr-only">Missing </span>
            {skillLabel(s)}
          </li>
        ))}
      </ul>
    </div>
  )
}

/* -------------------------------------------------------------- breakdown */
function Breakdown({ row, weights, usingWhatIf, jobTitle }) {
  if (!row) return null
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-6">
        <div className="min-w-0 flex-1">
          <p className="text-sm text-muted">Overall score</p>
          <p className="mt-1 flex items-baseline gap-2">
            <AnimatedNumber value={row.overall_score} className="text-3xl font-semibold tracking-tight text-ink" />
            <span className="text-base text-faint">/ 100</span>
          </p>
          <p className="tnum mt-1 text-base text-muted">
            Ranked <span className="font-semibold text-ink">#{row.rank}</span> for {jobTitle}
          </p>
        </div>
        <div className="w-[17rem] shrink-0">
          <RadarChart series={[{ label: row.full_name, values: row }]} size={170} />
        </div>
      </div>

      <p className="rounded-lg border border-line bg-canvas px-4 py-3 text-base text-ink">{row.explanation}</p>

      {row.insights.length > 0 && (
        <div data-tour="keyword" className="rounded-lg border border-accent/30 bg-accent-soft px-4 py-3">
          <h4 className="flex items-center gap-2 text-base font-semibold text-accent-ink">
            <SearchX size={16} aria-hidden /> Why a keyword search would miss this
          </h4>
          <ul className="mt-1.5 space-y-1 text-base text-ink">
            {row.insights.map((t) => (
              <li key={t} className="flex gap-2">
                <span className="mt-2.5 h-1 w-1 shrink-0 rounded-full bg-accent" aria-hidden />
                <span>{t}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="grid grid-cols-2 gap-x-6 gap-y-4">
        {METRICS.map((m) => (
          <MetricBar key={m.key} label={`${m.long} · weight ${weights[m.key]}%`} value={row[m.field]} />
        ))}
      </div>

      <div>
        <div className="flex items-baseline justify-between gap-3">
          <h4 className="text-sm font-medium text-ink">Exact calculation</h4>
          <p className="text-xs text-faint">{usingWhatIf ? 'Using your what-if weights' : 'Using the weights saved with this run'}</p>
        </div>
        <p className="tnum mt-2 overflow-x-auto whitespace-nowrap rounded border border-line bg-canvas px-3 py-2.5 font-mono text-[0.8125rem] text-ink">
          {calculation(row, weights)}
        </p>
      </div>

      <div className="space-y-4 border-t border-line pt-5">
        <SkillGroup title="Required skills" matched={row.matched.required} missing={row.missing.required} aliases={row.aliases} />
        <SkillGroup title="Preferred skills" matched={row.matched.preferred} missing={row.missing.preferred} aliases={row.aliases} />
      </div>

      <div className="border-t border-line pt-5 text-sm text-muted">
        {row.previous_titles && <p>Previous titles: {row.previous_titles}</p>}
        <p>
          {years(row.years_experience)} experience · {row.level_name}
        </p>
      </div>
    </div>
  )
}

/* ---------------------------------------------------------------- compare */
function Compare({ rows, weights }) {
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-8">
        <div className="w-[22rem] shrink-0">
          <RadarChart series={rows.map((r) => ({ label: r.full_name, values: r }))} size={240} />
        </div>
        <ul className="space-y-2" aria-label="Chart legend">
          {rows.map((r, i) => (
            <li key={r.candidate_id} className="flex items-center gap-2.5 text-base text-ink">
              <svg width="28" height="8" aria-hidden>
                <line x1="1" y1="4" x2="27" y2="4" stroke={SERIES_STYLES[i].stroke} strokeWidth="2.5" strokeDasharray={SERIES_STYLES[i].dash} />
              </svg>
              {r.full_name}
            </li>
          ))}
        </ul>
      </div>
      <div className="grid gap-px overflow-hidden rounded-lg border border-line bg-line" style={{ gridTemplateColumns: `repeat(${rows.length}, minmax(0, 1fr))` }}>
        {rows.map((r) => (
          <div key={r.candidate_id} className="space-y-4 bg-surface p-4">
            <div>
              <p className="tnum text-sm text-muted">Rank #{r.rank}</p>
              <p className="truncate text-md font-semibold text-ink">{r.full_name}</p>
              <p className="truncate text-sm text-faint">{r.previous_titles || '–'}</p>
            </div>
            <p className="tnum text-3xl font-semibold tracking-tight text-ink">{r.overall_score.toFixed(1)}</p>
            <div className="space-y-3">
              {METRICS.map((m) => (
                <MetricBar key={m.key} label={m.long} value={r[m.field]} />
              ))}
            </div>
            <div className="space-y-1 border-t border-line pt-3 text-sm">
              <p className="text-ink">
                <span className="tnum font-medium">
                  {r.matched.required.length} of {r.matched.required.length + r.missing.required.length}
                </span>{' '}
                required skills
              </p>
              {r.missing.required.length > 0 && <p className="text-muted">Missing: {r.missing.required.map(skillLabel).join(', ')}</p>}
              <p className="text-muted">
                {years(r.years_experience)} · {r.level_name}
              </p>
            </div>
            <p className="border-t border-line pt-3 text-sm text-muted">{r.explanation}</p>
          </div>
        ))}
      </div>
      <p className="text-sm text-faint">
        Weights: Skills {weights.skills}% · Experience {weights.experience}% · Education {weights.education}% · Meaning {weights.semantic}%
      </p>
    </div>
  )
}

/* -------------------------------------------------------------------- row */
function ResultRow({ row, baseRank, entranceDelay, explain, selected, onOpen, checked, onToggle, compareFull, moved }) {
  const delta = baseRank - row.rank
  const top3 = row.rank <= 3
  return (
    <motion.li
      layout="position"
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{
        opacity: { duration: 0.3, delay: entranceDelay },
        y: { duration: 0.35, delay: entranceDelay, ease: [0.16, 1, 0.3, 1] },
        layout: { type: 'spring', stiffness: 380, damping: 36, mass: 0.8 },
      }}
      className={`relative border-b border-line last:border-b-0 ${selected ? 'bg-accent-soft/50' : 'bg-surface hover:bg-canvas'}`}
      data-testid="result-row"
      data-rank={row.rank}
    >
      <AnimatePresence>
        {top3 && (
          <motion.span
            initial={{ scaleY: 0 }}
            animate={{ scaleY: 1 }}
            exit={{ scaleY: 0 }}
            transition={{ duration: 0.25 }}
            className="absolute inset-y-0 left-0 w-[3px] origin-top bg-accent"
            aria-hidden
          />
        )}
      </AnimatePresence>
      <div className={`${GRID} px-5 py-3.5`}>
        <input
          type="checkbox"
          checked={checked}
          disabled={!checked && compareFull}
          onChange={onToggle}
          className="relative z-10 h-4 w-4 cursor-pointer rounded border-line-strong accent-[rgb(var(--accent))] disabled:cursor-not-allowed disabled:opacity-40"
          aria-label={`Compare ${row.full_name}`}
        />
        <div className="tnum flex items-center gap-1">
          <span className={`text-lg font-semibold ${top3 ? 'text-accent' : 'text-muted'}`}>{row.rank}</span>
          {moved && delta !== 0 && (
            <span className={`flex items-center text-2xs font-medium ${delta > 0 ? 'text-accent' : 'text-faint'}`} title={`Was #${baseRank}`}>
              {delta > 0 ? <ArrowUp size={10} aria-hidden /> : <ArrowDown size={10} aria-hidden />}
              {Math.abs(delta)}
              <span className="sr-only">{delta > 0 ? 'places up' : 'places down'} from #{baseRank}</span>
            </span>
          )}
        </div>
        <button type="button" onClick={onOpen} className="min-w-0 text-left after:absolute after:inset-0 after:content-['']" aria-label={`Open breakdown for ${row.full_name}, rank ${row.rank}, overall ${row.overall_score.toFixed(1)}`}>
          <span className="block truncate text-md font-semibold text-ink">{row.full_name}</span>
          <span className="block truncate text-sm text-faint">{row.previous_titles || `${years(row.years_experience)} · ${row.level_name}`}</span>
        </button>
        <div className="text-right">
          <AnimatedNumber value={row.overall_score} delay={entranceDelay} className="text-2xl font-semibold tracking-tight text-ink" />
        </div>
        {METRICS.map((m) => (
          <MetricBar key={m.key} label={m.label} value={row[m.field]} delay={entranceDelay + 0.08} hideLabel />
        ))}
        <ChevronRight size={16} className="text-faint" aria-hidden />
      </div>
      <AnimatePresence initial={false}>
        {explain && (
          <motion.p
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden pl-[6.75rem] pr-5 text-base text-muted"
          >
            <span className="block pb-3.5">{row.explanation}</span>
          </motion.p>
        )}
      </AnimatePresence>
    </motion.li>
  )
}

/* ------------------------------------------------------------------- page */
export default function Results() {
  const { jobId } = useParams()
  const location = useLocation()
  const navigate = useNavigate()
  const toast = useToast()
  const [jobs, setJobs] = useState(null)
  const [data, setData] = useState(location.state?.fresh || null)
  const [loading, setLoading] = useState(!location.state?.fresh)
  const [weights, setWeights] = useState(location.state?.fresh?.run ? weightsOf(location.state.fresh.run) : null)
  const [whatIfOpen, setWhatIfOpen] = useState(false)
  const [explain, setExplain] = useState(false)
  const [selectedId, setSelectedId] = useState(null)
  const [compareIds, setCompareIds] = useState([])
  const [compareOpen, setCompareOpen] = useState(false)
  const [visible, setVisible] = useState(PAGE)
  const [running, setRunning] = useState(false)
  const [tourOpen, setTourOpen] = useState(false)
  const [entranceKey, setEntranceKey] = useState(0)
  const mountBase = useRef(0)
  const tourRequested = useRef(Boolean(location.state?.tour) || demoState.tourPending)

  const id = jobId ? Number(jobId) : null

  useEffect(() => {
    api.listJobs().then(setJobs).catch(() => setJobs([]))
  }, [])

  // /results without a job: go to the most recently matched job.
  useEffect(() => {
    if (id || !jobs) return
    const withRun = jobs.filter((j) => j.last_run_at).sort((a, b) => (a.last_run_at < b.last_run_at ? 1 : -1))
    if (withRun.length) navigate(`/results/${withRun[0].job_id}`, { replace: true })
    else setLoading(false)
  }, [id, jobs, navigate])

  const applyData = useCallback((d) => {
    setData(d)
    setWeights(d.run ? weightsOf(d.run) : null)
    setVisible(PAGE)
    mountBase.current = 0
    setSelectedId(null)
    setCompareIds([])
    setEntranceKey((k) => k + 1)
  }, [])

  useEffect(() => {
    if (!id) return
    if (location.state?.fresh && location.state.fresh.job.job_id === id && data === location.state.fresh) {
      // Arrived straight from Run Match: render immediately, then drop the
      // navigation state so a refresh refetches instead of replaying.
      navigate(location.pathname, { replace: true, state: null })
      return
    }
    if (data && data.job.job_id === id && !location.state) return
    setLoading(true)
    api
      .getResults(id)
      .then(applyData)
      .catch((e) => toast.error('Could not load results', e.detail))
      .finally(() => setLoading(false))
  }, [id]) // eslint-disable-line react-hooks/exhaustive-deps

  const runWeights = data?.run ? weightsOf(data.run) : null
  const usingWhatIf = Boolean(weights && runWeights && !sameWeights(weights, runWeights))
  const base = data?.results || []
  const baseRank = useMemo(() => new Map(base.map((r) => [r.candidate_id, r.rank])), [base])
  const rows = useMemo(() => (weights && usingWhatIf ? rerank(base, weights) : base), [base, weights, usingWhatIf])
  const byId = useMemo(() => new Map(rows.map((r) => [r.candidate_id, r])), [rows])
  const selected = selectedId != null ? byId.get(selectedId) : null
  const shown = rows.slice(0, visible)

  const rerun = async () => {
    setRunning(true)
    try {
      const d = await api.runMatch(id)
      applyData(d)
      toast.success('Match complete', `${d.run.candidate_count.toLocaleString()} candidates ranked in ${duration(d.run.duration_ms)}`)
    } catch (e) {
      toast.error('Match could not run', e.detail)
    } finally {
      setRunning(false)
    }
  }

  const toggleCompare = (cid) =>
    setCompareIds((ids) => (ids.includes(cid) ? ids.filter((x) => x !== cid) : ids.length >= 3 ? ids : [...ids, cid]))

  // ---------------------------------------------------------- guided tour
  const rescueRow = useMemo(() => {
    // The clearest example: the biggest gap between meaning match and skills match.
    const semantic = rows
      .filter((r) => r.insights.some((t) => t.includes('different words')))
      .sort((a, b) => b.semantic_score - b.skills_score - (a.semantic_score - a.skills_score))[0]
    return semantic || rows.find((r) => r.insights.length) || rows[0]
  }, [rows])

  const tourSteps = useMemo(
    () => [
      {
        target: '[data-tour="results"]',
        title: 'The ranked shortlist',
        body: (
          <>
            All {base.length.toLocaleString()} candidates were scored against this job in {data?.run ? duration(data.run.duration_ms) : '–'}. The top three
            carry a blue edge. Every bar also shows its number, so nothing relies on colour.
          </>
        ),
        placement: 'bottom',
        onEnter: () => {
          setSelectedId(null)
          setWhatIfOpen(false)
        },
      },
      {
        target: '[data-tour="breakdown"]',
        title: `Why ${rows[0]?.full_name} is first`,
        body: 'Matched and missing skills, a plain-English summary, and the exact calculation behind the overall score.',
        placement: 'left',
        onEnter: () => setSelectedId(rows[0]?.candidate_id ?? null),
      },
      {
        target: '[data-tour="keyword"]',
        title: 'What a keyword search would miss',
        body: `${rescueRow?.full_name} describes this work in their own words rather than listing every tool. The meaning match still finds them.`,
        placement: 'left',
        onEnter: () => setSelectedId(rescueRow?.candidate_id ?? null),
      },
      {
        target: '[data-tour="weights"]',
        title: 'Ask “what if?”',
        body: 'Drag any slider. The list re-ranks instantly in the browser without re-running the match. Try raising Meaning match.',
        placement: 'bottom-end',
        dim: false,
        onEnter: () => {
          setSelectedId(null)
          setWhatIfOpen(true)
          window.scrollTo({ top: 0, behavior: 'smooth' })
        },
      },
    ],
    [rows, rescueRow, base.length, data],
  )

  useEffect(() => {
    if (tourRequested.current && data?.results?.length) {
      tourRequested.current = false
      demoState.tourPending = false
      const t = setTimeout(() => setTourOpen(true), Math.min(rows.length, 12) * STAGGER * 1000 + 900)
      return () => clearTimeout(t)
    }
    return undefined
  }, [data]) // eslint-disable-line react-hooks/exhaustive-deps

  // ---------------------------------------------------------------- render
  if (!id && jobs && !loading) {
    return (
      <div className="panel">
        <EmptyState
          icon={Trophy}
          title="No results yet"
          action={
            <Link to="/jobs" className="btn-primary">
              Go to job specifications
            </Link>
          }
        >
          Open a job specification and press Run Match. The ranked shortlist will appear here.
        </EmptyState>
      </div>
    )
  }

  const job = data?.job
  const run = data?.run

  return (
    <div>
      {/* Header */}
      <div className="mb-5 flex flex-wrap items-end justify-between gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-3">
            <p className="text-sm text-faint">Results for</p>
            {jobs && jobs.length > 1 && (
              <div className="relative">
                <label htmlFor="job-switch" className="sr-only">
                  Switch job
                </label>
                <select
                  id="job-switch"
                  value={id || ''}
                  onChange={(e) => navigate(`/results/${e.target.value}`)}
                  className="h-6 cursor-pointer appearance-none rounded border border-line bg-surface pl-2 pr-6 text-xs font-medium text-muted hover:border-line-strong hover:text-ink focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/30"
                >
                  {jobs.map((j) => (
                    <option key={j.job_id} value={j.job_id}>
                      {j.job_title}
                    </option>
                  ))}
                </select>
                <ChevronDown size={12} className="pointer-events-none absolute right-1.5 top-1/2 -translate-y-1/2 text-faint" aria-hidden />
              </div>
            )}
          </div>
          <h1 className="mt-0.5 truncate text-2xl font-semibold tracking-tight text-ink">{job?.job_title || 'Results'}</h1>
          {run ? (
            <p className="tnum mt-1 text-sm text-muted">
              Matched {timeAgo(run.run_at)} · {run.candidate_count.toLocaleString()} candidates ranked in {duration(run.duration_ms)} · weights{' '}
              {run.w_skills} / {run.w_experience} / {run.w_education} / {run.w_semantic}
            </p>
          ) : (
            !loading && <p className="mt-1 text-sm text-muted">Not matched yet.</p>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button type="button" className={`btn-secondary ${explain ? 'border-accent/40 bg-accent-soft text-accent-ink' : ''}`} onClick={() => setExplain((x) => !x)} aria-pressed={explain} disabled={!rows.length}>
            <MessageSquareText size={15} aria-hidden /> Explain this ranking
          </button>
          <button type="button" className={`btn-secondary ${whatIfOpen ? 'border-accent/40 bg-accent-soft text-accent-ink' : ''}`} onClick={() => setWhatIfOpen((x) => !x)} aria-expanded={whatIfOpen} disabled={!rows.length}>
            <SlidersHorizontal size={15} aria-hidden /> What if
          </button>
          {run && (
            <a className="btn-secondary" href={api.csvUrl(id)} download>
              <Download size={15} aria-hidden /> Export CSV
            </a>
          )}
          <button type="button" className="btn-go" onClick={rerun} disabled={!id || running}>
            {running ? <Spinner /> : <Zap size={15} aria-hidden />}
            {running ? 'Matching…' : run ? 'Run Match again' : 'Run Match'}
          </button>
        </div>
      </div>

      {/* What-if weights */}
      <AnimatePresence initial={false}>
        {whatIfOpen && weights && (
          <motion.section
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: [0.2, 0.8, 0.2, 1] }}
            className="overflow-hidden"
            aria-label="What if weights"
          >
            <div data-tour="weights" className="panel mb-5 grid gap-6 p-5 lg:grid-cols-[16rem_minmax(0,1fr)]">
              <div>
                <h2 className="text-md font-semibold text-ink">What if the weights were different?</h2>
                <p className="mt-1 text-sm text-muted">
                  Drag a slider and the others adjust to keep 100%. The list re-ranks instantly from the saved scores. Nothing is saved.
                </p>
                {usingWhatIf && (
                  <p className="mt-3 inline-flex items-center gap-1.5 rounded border border-accent/30 bg-accent-soft px-2 py-1 text-sm font-medium text-accent-ink">
                    Showing what-if ranking
                  </p>
                )}
              </div>
              <WeightSliders
                idPrefix="whatif"
                mode="balanced"
                dense
                weights={weights}
                onChange={setWeights}
                onReset={() => setWeights(runWeights)}
                resetLabel="Back to the run's weights"
              />
            </div>
          </motion.section>
        )}
      </AnimatePresence>

      {/* Results list */}
      <div className="panel overflow-hidden" data-tour="results">
        <div className="overflow-x-auto">
          <div className="min-w-[62rem]">
            <div className={`${GRID} border-b border-line bg-canvas px-5 py-2.5`}>
              <span>
                <span className="sr-only">Compare</span>
              </span>
              <span className="th">Rank</span>
              <span className="th">Candidate</span>
              <span className="th text-right">Overall</span>
              {METRICS.map((m) => (
                <span key={m.key} className="th">
                  {m.label}
                  {weights && <span className="tnum ml-1 normal-case tracking-normal text-faint/80">{weights[m.key]}%</span>}
                </span>
              ))}
              <span />
            </div>

            {loading ? (
              <div>
                {Array.from({ length: 7 }).map((_, i) => (
                  <div key={i} className={`${GRID} border-b border-line px-5 py-4`}>
                    <Skeleton className="h-4 w-4" />
                    <Skeleton className="h-5 w-6" />
                    <div>
                      <Skeleton className="h-4 w-36" />
                      <Skeleton className="mt-1.5 h-3 w-24" />
                    </div>
                    <Skeleton className="ml-auto h-7 w-14" />
                    {[0, 1, 2, 3].map((k) => (
                      <Skeleton key={k} className="h-6 w-full" />
                    ))}
                    <span />
                  </div>
                ))}
              </div>
            ) : !run ? (
              <EmptyState
                icon={Zap}
                title="This job has not been matched yet"
                action={
                  <button type="button" className="btn-go" onClick={rerun} disabled={running}>
                    {running ? <Spinner /> : <Zap size={15} aria-hidden />} Run Match
                  </button>
                }
              >
                Run the match to rank every candidate against {job?.job_title || 'this job'}.
              </EmptyState>
            ) : (
              <LayoutGroup>
                <ol key={entranceKey} aria-label="Ranked candidates">
                  {shown.map((r, i) => (
                    <ResultRow
                      key={r.candidate_id}
                      row={r}
                      baseRank={baseRank.get(r.candidate_id)}
                      entranceDelay={Math.max(0, Math.min(i - mountBase.current, 14)) * STAGGER}
                      explain={explain}
                      selected={r.candidate_id === selectedId}
                      onOpen={() => setSelectedId(r.candidate_id)}
                      checked={compareIds.includes(r.candidate_id)}
                      onToggle={() => toggleCompare(r.candidate_id)}
                      compareFull={compareIds.length >= 3}
                      moved={usingWhatIf}
                    />
                  ))}
                </ol>
              </LayoutGroup>
            )}
          </div>
        </div>
        {run && rows.length > visible && (
          <div className="flex items-center justify-between border-t border-line bg-canvas px-5 py-3">
            <span className="tnum text-sm text-muted">
              Showing top {visible.toLocaleString()} of {rows.length.toLocaleString()}
            </span>
            <button
              type="button"
              className="btn-secondary btn-sm"
              onClick={() => {
                mountBase.current = visible
                setVisible((n) => n + PAGE)
              }}
            >
              Show {Math.min(PAGE, rows.length - visible)} more
            </button>
          </div>
        )}
      </div>

      {/* Compare tray */}
      <AnimatePresence>
        {compareIds.length > 0 && (
          <motion.div
            initial={{ y: 24, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: 24, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-x-0 bottom-5 z-30 mx-auto flex w-fit items-center gap-3 rounded-lg border border-line bg-surface py-2 pl-4 pr-2 shadow-pop"
            role="region"
            aria-label="Compare selection"
          >
            <span className="tnum text-base text-ink">
              {compareIds.length} selected <span className="text-faint">· up to 3</span>
            </span>
            <button type="button" className="btn-ghost btn-sm" onClick={() => setCompareIds([])}>
              Clear
            </button>
            <button type="button" className="btn-primary btn-sm" disabled={compareIds.length < 2} onClick={() => setCompareOpen(true)}>
              <Columns3 size={14} aria-hidden /> Compare {compareIds.length >= 2 ? compareIds.length : ''} head to head
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      <SlideOver
        open={Boolean(selected)}
        onClose={() => setSelectedId(null)}
        title={selected?.full_name}
        subtitle={selected ? `Rank #${selected.rank} · ${selected.previous_titles || selected.level_name}` : ''}
        width="w-[36rem]"
        tourId="breakdown"
      >
        <Breakdown row={selected} weights={weights || {}} usingWhatIf={usingWhatIf} jobTitle={job?.job_title} />
      </SlideOver>

      <SlideOver
        open={compareOpen && compareIds.length >= 2}
        onClose={() => setCompareOpen(false)}
        title="Head to head"
        subtitle={job?.job_title}
        width="w-[60rem]"
      >
        <Compare rows={compareIds.map((cid) => byId.get(cid)).filter(Boolean).sort((a, b) => a.rank - b.rank)} weights={weights || {}} />
      </SlideOver>

      <Tour steps={tourSteps} open={tourOpen} onClose={() => setTourOpen(false)} />
    </div>
  )
}
