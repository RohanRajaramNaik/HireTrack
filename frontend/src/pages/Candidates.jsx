import { useVirtualizer } from '@tanstack/react-virtual'
import { ArrowDown, ArrowUp, ChevronsUpDown, Pencil, Plus, Search, Trash2, Users, X } from 'lucide-react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../apiClient'
import { ConfirmDialog, SlideOver } from '../components/Overlay'
import TagInput from '../components/TagInput'
import { useToast } from '../components/Toast'
import { EmptyState, Field, PageHeader, Skeleton, Spinner } from '../components/ui'
import { years } from '../lib/format'
import { useDebounced, useEducationLevels } from '../lib/hooks'
import { normaliseSkill, validateCandidate } from '../lib/validation'

const ROW_H = 60
const COLS = 'grid grid-cols-[minmax(12rem,1.3fr)_minmax(10rem,1fr)_minmax(14rem,1.6fr)_6rem_10rem_3rem] items-center gap-4'

const EMPTY = { full_name: '', email: '', years_experience: '', level_id: '', previous_titles: '', resume_summary: '', skills: [] }

const SORTS = {
  name: (a, b) => a.full_name.localeCompare(b.full_name),
  years: (a, b) => a.years_experience - b.years_experience,
  level: (a, b) => a.level_id - b.level_id,
  skills: (a, b) => a.skills.length - b.skills.length,
}

function SortHeader({ id, label, sort, setSort, className = '' }) {
  const active = sort.key === id
  const Icon = !active ? ChevronsUpDown : sort.dir === 'asc' ? ArrowUp : ArrowDown
  return (
    <button
      type="button"
      onClick={() => setSort({ key: id, dir: active && sort.dir === 'asc' ? 'desc' : 'asc' })}
      className={`th inline-flex items-center gap-1 hover:text-ink ${active ? 'text-ink' : ''} ${className}`}
      aria-sort={active ? (sort.dir === 'asc' ? 'ascending' : 'descending') : 'none'}
    >
      {label}
      <Icon size={12} aria-hidden />
    </button>
  )
}

function CandidateForm({ initial, levels, onSaved, onClose, onDelete }) {
  const [v, setV] = useState(initial)
  const [errors, setErrors] = useState({})
  const [submitted, setSubmitted] = useState(false)
  const [saving, setSaving] = useState(false)
  const toast = useToast()
  const editing = Boolean(initial.candidate_id)

  const set = (k) => (e) => {
    const next = { ...v, [k]: e && e.target ? e.target.value : e }
    setV(next)
    if (submitted) setErrors(validateCandidate(next))
  }

  const submit = async (e) => {
    e.preventDefault()
    setSubmitted(true)
    const errs = validateCandidate(v)
    setErrors(errs)
    if (Object.keys(errs).length) {
      document.querySelector('[aria-invalid="true"]')?.focus()
      return
    }
    setSaving(true)
    const body = {
      full_name: v.full_name.trim(),
      email: v.email.trim() || null,
      years_experience: Number(v.years_experience),
      level_id: Number(v.level_id),
      previous_titles: v.previous_titles.trim() || null,
      resume_summary: v.resume_summary.trim(),
      skills: v.skills,
    }
    try {
      const saved = editing ? await api.updateCandidate(initial.candidate_id, body) : await api.createCandidate(body)
      toast.success(editing ? 'Candidate updated' : 'Candidate added', saved.full_name)
      onSaved(saved)
    } catch (err) {
      if (err.field) setErrors({ [err.field]: err.detail })
      else toast.error('Could not save candidate', err.detail)
    } finally {
      setSaving(false)
    }
  }

  return (
    <form id="candidate-form" onSubmit={submit} noValidate className="space-y-5">
      <Field label="Full name" error={errors.full_name}>
        {({ id, invalid, describedBy }) => (
          <input id={id} className="input" value={v.full_name} onChange={set('full_name')} aria-invalid={invalid} aria-describedby={describedBy} maxLength={120} autoComplete="off" />
        )}
      </Field>
      <Field label="Email" optional error={errors.email} hint="Stored for contact only. Never used in scoring.">
        {({ id, invalid, describedBy }) => (
          <input id={id} type="email" className="input" value={v.email} onChange={set('email')} aria-invalid={invalid} aria-describedby={describedBy} autoComplete="off" />
        )}
      </Field>
      <div className="grid grid-cols-2 gap-4">
        <Field label="Years of experience" error={errors.years_experience}>
          {({ id, invalid, describedBy }) => (
            <input id={id} type="number" min={0} max={50} step={0.5} className="input tnum" value={v.years_experience} onChange={set('years_experience')} aria-invalid={invalid} aria-describedby={describedBy} />
          )}
        </Field>
        <Field label="Highest education" error={errors.level_id}>
          {({ id, invalid, describedBy }) => (
            <select id={id} className="input" value={v.level_id} onChange={set('level_id')} aria-invalid={invalid} aria-describedby={describedBy}>
              <option value="">Choose a level</option>
              {levels.map((l) => (
                <option key={l.level_id} value={l.level_id}>
                  {l.level_name}
                </option>
              ))}
            </select>
          )}
        </Field>
      </div>
      <Field label="Previous job titles" optional hint="Separate titles with a semicolon.">
        {({ id, describedBy }) => (
          <input id={id} className="input" value={v.previous_titles} onChange={set('previous_titles')} aria-describedby={describedBy} maxLength={500} />
        )}
      </Field>
      <Field label="Skills" error={errors.skills} hint="Press Enter after each skill. Abbreviations like JS or K8s are understood.">
        {({ id, invalid, describedBy }) => (
          <TagInput id={id} label="Skills" value={v.skills} onChange={set('skills')} invalid={invalid} describedBy={describedBy} />
        )}
      </Field>
      <Field label="Resume summary" error={errors.resume_summary} count={v.resume_summary.trim().length} max={3000} hint="A few sentences on the work they have done. Used for the meaning match.">
        {({ id, invalid, describedBy }) => (
          <textarea id={id} rows={7} className="input" value={v.resume_summary} onChange={set('resume_summary')} aria-invalid={invalid} aria-describedby={describedBy} />
        )}
      </Field>
      <div className="flex items-center gap-2 border-t border-line pt-4">
        {editing && (
          <button type="button" className="btn-danger-ghost -ml-2" onClick={onDelete}>
            <Trash2 size={15} aria-hidden /> Delete
          </button>
        )}
        <div className="ml-auto flex gap-2">
          <button type="button" className="btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="btn-primary" disabled={saving}>
            {saving && <Spinner />}
            {editing ? 'Save changes' : 'Add candidate'}
          </button>
        </div>
      </div>
    </form>
  )
}

export default function Candidates() {
  const [rows, setRows] = useState(null)
  const [query, setQuery] = useState('')
  const [sort, setSort] = useState({ key: 'name', dir: 'asc' })
  const [editing, setEditing] = useState(null) // null | {} (new) | candidate
  const [confirmDelete, setConfirmDelete] = useState(null)
  const [deleting, setDeleting] = useState(false)
  const levels = useEducationLevels()
  const toast = useToast()
  const debounced = useDebounced(query, 120)
  const scrollRef = useRef(null)

  const load = useCallback(() => {
    api
      .listCandidates()
      .then((r) => setRows(r.items))
      .catch((e) => {
        setRows([])
        toast.error('Could not load candidates', e.detail)
      })
  }, [toast])

  useEffect(load, [load])

  const filtered = useMemo(() => {
    if (!rows) return []
    const q = debounced.trim().toLowerCase()
    const qSkill = normaliseSkill(q)
    let list = rows
    if (q) {
      list = rows.filter(
        (c) =>
          c.full_name.toLowerCase().includes(q) ||
          (c.previous_titles || '').toLowerCase().includes(q) ||
          (c.email || '').toLowerCase().includes(q) ||
          c.skills.some((s) => s.toLowerCase().includes(q) || normaliseSkill(s).includes(qSkill)),
      )
    }
    const cmp = SORTS[sort.key]
    const sorted = [...list].sort((a, b) => cmp(a, b) || a.full_name.localeCompare(b.full_name))
    return sort.dir === 'desc' ? sorted.reverse() : sorted
  }, [rows, debounced, sort])

  const virtualizer = useVirtualizer({
    count: filtered.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => ROW_H,
    overscan: 12,
  })

  const onSaved = (saved) => {
    setRows((prev) => {
      const exists = prev.some((c) => c.candidate_id === saved.candidate_id)
      return exists ? prev.map((c) => (c.candidate_id === saved.candidate_id ? saved : c)) : [saved, ...prev]
    })
    setEditing(null)
  }

  const doDelete = async () => {
    setDeleting(true)
    try {
      await api.deleteCandidate(confirmDelete.candidate_id)
      setRows((prev) => prev.filter((c) => c.candidate_id !== confirmDelete.candidate_id))
      toast.success('Candidate deleted', `${confirmDelete.full_name} and their match results were removed.`)
      setConfirmDelete(null)
      setEditing(null)
    } catch (e) {
      toast.error('Could not delete candidate', e.detail)
    } finally {
      setDeleting(false)
    }
  }

  const total = rows ? rows.length : 0

  return (
    <div>
      <PageHeader
        title="Candidates"
        description={rows ? `${total.toLocaleString()} candidate${total === 1 ? '' : 's'} in the database` : 'Loading candidates'}
        actions={
          <button type="button" className="btn-primary" onClick={() => setEditing({ ...EMPTY })}>
            <Plus size={16} aria-hidden /> Add candidate
          </button>
        }
      />

      <div className="panel overflow-hidden">
        <div className="flex items-center gap-3 border-b border-line px-4 py-3">
          <div className="relative w-full max-w-sm">
            <Search size={15} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-faint" aria-hidden />
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search by name, title or skill"
              className="input pl-9 pr-8"
              aria-label="Search candidates"
            />
            {query && (
              <button type="button" onClick={() => setQuery('')} className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-faint hover:text-ink" aria-label="Clear search">
                <X size={14} />
              </button>
            )}
          </div>
          {rows && debounced && (
            <span className="tnum text-sm text-muted" aria-live="polite">
              {filtered.length.toLocaleString()} of {total.toLocaleString()} shown
            </span>
          )}
        </div>

        <div className="overflow-x-auto">
          <div className="min-w-[60rem]">
            <div className={`${COLS} border-b border-line bg-canvas px-4 py-2.5`} role="row">
              <SortHeader id="name" label="Name" sort={sort} setSort={setSort} />
              <span className="th">Previous titles</span>
              <SortHeader id="skills" label="Skills" sort={sort} setSort={setSort} />
              <SortHeader id="years" label="Experience" sort={sort} setSort={setSort} />
              <SortHeader id="level" label="Education" sort={sort} setSort={setSort} />
              <span className="sr-only">Actions</span>
            </div>

            {rows === null ? (
              <div className="divide-y divide-line">
                {Array.from({ length: 8 }).map((_, i) => (
                  <div key={i} className={`${COLS} px-4`} style={{ height: ROW_H }}>
                    <Skeleton className="h-4 w-40" />
                    <Skeleton className="h-4 w-32" />
                    <Skeleton className="h-5 w-52" />
                    <Skeleton className="h-4 w-12" />
                    <Skeleton className="h-4 w-24" />
                    <span />
                  </div>
                ))}
              </div>
            ) : total === 0 ? (
              <EmptyState
                icon={Users}
                title="No candidates yet"
                action={
                  <div className="flex gap-2">
                    <button type="button" className="btn-primary" onClick={() => setEditing({ ...EMPTY })}>
                      <Plus size={16} aria-hidden /> Add candidate
                    </button>
                    <Link to="/admin" className="btn-secondary">
                      Load demo data
                    </Link>
                  </div>
                }
              >
                Add your first candidate, or load the demo data from the Admin screen.
              </EmptyState>
            ) : filtered.length === 0 ? (
              <EmptyState icon={Search} title={`Nothing matches “${debounced}”`}>
                Try a shorter search, or search by a single skill such as Python.
              </EmptyState>
            ) : (
              <div ref={scrollRef} className="max-h-[calc(100vh-17rem)] min-h-[20rem] overflow-y-auto" data-testid="candidate-scroll">
                <div style={{ height: virtualizer.getTotalSize(), position: 'relative' }}>
                  {virtualizer.getVirtualItems().map((vr) => {
                    const c = filtered[vr.index]
                    const shown = c.skills.slice(0, 4)
                    return (
                      <div
                        key={c.candidate_id}
                        className={`${COLS} group absolute inset-x-0 cursor-pointer border-b border-line px-4 hover:bg-canvas`}
                        style={{ height: ROW_H, transform: `translateY(${vr.start}px)` }}
                        onClick={() => setEditing(c)}
                        role="row"
                      >
                        <div className="min-w-0">
                          <p className="truncate text-base font-medium text-ink">{c.full_name}</p>
                          <p className="truncate text-sm text-faint">{c.email || 'No email'}</p>
                        </div>
                        <p className="truncate text-sm text-muted">{c.previous_titles || '–'}</p>
                        <div className="flex min-w-0 items-center gap-1 overflow-hidden">
                          {shown.map((s) => (
                            <span key={s} className="chip shrink-0">
                              {s}
                            </span>
                          ))}
                          {c.skills.length > shown.length && <span className="tnum shrink-0 text-sm text-faint">+{c.skills.length - shown.length}</span>}
                        </div>
                        <p className="tnum text-base text-ink">{years(c.years_experience)}</p>
                        <p className="truncate text-sm text-muted">{c.level_name}</p>
                        <button
                          type="button"
                          className="btn-ghost btn-sm px-1.5 opacity-60 group-hover:opacity-100 focus:opacity-100"
                          onClick={(e) => {
                            e.stopPropagation()
                            setEditing(c)
                          }}
                          aria-label={`Edit ${c.full_name}`}
                        >
                          <Pencil size={14} />
                        </button>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      <SlideOver
        open={editing !== null}
        onClose={() => setEditing(null)}
        title={editing?.candidate_id ? 'Edit candidate' : 'Add candidate'}
        subtitle={editing?.candidate_id ? editing.full_name : 'Only skills, experience, education and the summary are scored.'}
      >
        {editing && (
          <CandidateForm
            key={editing.candidate_id || 'new'}
            initial={{
              ...EMPTY,
              ...editing,
              email: editing.email || '',
              previous_titles: editing.previous_titles || '',
              years_experience: editing.years_experience ?? '',
              level_id: editing.level_id ? String(editing.level_id) : '',
            }}
            levels={levels}
            onSaved={onSaved}
            onClose={() => setEditing(null)}
            onDelete={() => setConfirmDelete(editing)}
          />
        )}
      </SlideOver>

      <ConfirmDialog
        open={Boolean(confirmDelete)}
        title={`Delete ${confirmDelete?.full_name}?`}
        confirmLabel="Delete candidate"
        busy={deleting}
        onConfirm={doDelete}
        onCancel={() => setConfirmDelete(null)}
      >
        Their profile and every match result that includes them will be permanently removed.
      </ConfirmDialog>
    </div>
  )
}
