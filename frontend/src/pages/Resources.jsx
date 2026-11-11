import { Briefcase, FolderKanban, Plus, Search, Trash2, Users } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { NavLink, useParams, useSearchParams } from 'react-router-dom'
import { api } from '../apiClient'
import { ConfirmDialog, SlideOver } from '../components/Overlay'
import { useToast } from '../components/Toast'
import { EmptyState, Field, PageHeader, Skeleton, Spinner } from '../components/ui'
import { useAuth } from '../lib/auth'
import { useDebounced } from '../lib/hooks'

const BANDS = {
  bench: 'On the bench',
  light: 'Light (1–49%)',
  healthy: 'Healthy (50–89%)',
  full: 'Full (90–100%)',
  inactive: 'Inactive',
}
const PROJECT_STATUS = { planned: 'Planned', active: 'Active', on_hold: 'On hold', completed: 'Completed' }

const fmtDate = (d) => new Date(d + 'T00:00:00').toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })
const todayIso = () => new Date().toISOString().slice(0, 10)

/** Utilisation as a thin bar plus the number (the bar is never the only cue). */
function Utilisation({ value }) {
  return (
    <div className="flex items-center gap-2.5">
      <span className="relative h-1.5 w-20 rounded-full bg-bar-track" aria-hidden>
        <span className="absolute inset-y-0 left-0 rounded-full bg-bar-fill" style={{ width: `${Math.min(value, 100)}%` }} />
      </span>
      <span className="tnum w-10 text-sm font-medium text-ink">{value}%</span>
    </div>
  )
}

function StatusChip({ status }) {
  const tone =
    status === 'active'
      ? 'border-accent/25 bg-accent-soft text-accent-ink'
      : status === 'completed'
        ? 'border-line bg-subtle text-muted'
        : status === 'on_hold'
          ? 'border-warn/30 bg-warn-soft text-ink'
          : 'border-line bg-surface text-ink'
  return <span className={`chip h-5 px-1.5 text-xs ${tone}`}>{PROJECT_STATUS[status]}</span>
}

/* ---------------------------------------------------------- allocations */
function AllocationForm({ fixedStaff, fixedProject, staffList, projectList, onSaved }) {
  const toast = useToast()
  const project = fixedProject || null
  const start0 = project ? (project.start_date > todayIso() ? project.start_date : todayIso()) : todayIso()
  const [v, setV] = useState({
    staff_id: fixedStaff ? String(fixedStaff.staff_id) : '',
    project_id: fixedProject ? String(fixedProject.project_id) : '',
    allocation_percent: '50',
    start_date: start0 > (project?.end_date || '9999') ? project.start_date : start0,
    end_date: project ? project.end_date : '',
    role_on_project: '',
  })
  const [errors, setErrors] = useState({})
  const [busy, setBusy] = useState(false)
  const set = (k) => (e) => setV((x) => ({ ...x, [k]: e.target.value }))

  const pickProject = (e) => {
    const p = projectList.find((x) => String(x.project_id) === e.target.value)
    setV((x) => ({
      ...x,
      project_id: e.target.value,
      start_date: p ? (p.start_date > todayIso() ? p.start_date : todayIso() > p.end_date ? p.start_date : todayIso()) : x.start_date,
      end_date: p ? p.end_date : x.end_date,
    }))
  }

  const submit = async (e) => {
    e.preventDefault()
    const errs = {}
    if (!v.staff_id) errs.staff_id = 'Choose a staff member'
    if (!v.project_id) errs.project_id = 'Choose a project'
    const pct = Number(v.allocation_percent)
    if (!Number.isInteger(pct) || pct < 1 || pct > 100) errs.allocation_percent = 'Enter a whole number from 1 to 100'
    if (!v.start_date) errs.start_date = 'Choose a start date'
    if (!v.end_date) errs.end_date = 'Choose an end date'
    else if (v.start_date && v.end_date < v.start_date) errs.end_date = 'End date cannot be before the start date'
    setErrors(errs)
    if (Object.keys(errs).length) return
    setBusy(true)
    try {
      const a = await api.createAllocation({
        staff_id: Number(v.staff_id),
        project_id: Number(v.project_id),
        allocation_percent: pct,
        start_date: v.start_date,
        end_date: v.end_date,
        role_on_project: v.role_on_project.trim() || null,
      })
      toast.success('Allocation saved', `${a.staff_name} on ${a.project_name} at ${a.allocation_percent}%`)
      onSaved(a)
      setV((x) => ({ ...x, staff_id: fixedStaff ? x.staff_id : '', role_on_project: '' }))
    } catch (err) {
      setErrors({ [err.field || 'allocation_percent']: err.detail })
    } finally {
      setBusy(false)
    }
  }

  const input = (k, label, props = {}) => (
    <Field label={label} error={errors[k]} {...(props.field || {})}>
      {({ id, invalid, describedBy }) => (
        <input id={id} className="input" value={v[k]} onChange={set(k)} aria-invalid={invalid} aria-describedby={describedBy} {...(props.input || {})} />
      )}
    </Field>
  )

  return (
    <form onSubmit={submit} noValidate className="space-y-4 rounded-lg border border-line bg-canvas p-4" data-testid="allocation-form">
      <h3 className="text-sm font-semibold text-ink">{fixedStaff ? 'Allocate to a project' : 'Allocate a staff member'}</h3>
      {!fixedStaff && (
        <Field label="Staff member" error={errors.staff_id}>
          {({ id, invalid, describedBy }) => (
            <select id={id} className="input" value={v.staff_id} onChange={set('staff_id')} aria-invalid={invalid} aria-describedby={describedBy}>
              <option value="">Choose a person</option>
              {staffList
                .filter((s) => s.is_active)
                .map((s) => (
                  <option key={s.staff_id} value={s.staff_id}>
                    {s.full_name} · {s.role_title} · {s.utilisation}% booked today
                  </option>
                ))}
            </select>
          )}
        </Field>
      )}
      {!fixedProject && (
        <Field label="Project" error={errors.project_id}>
          {({ id, invalid, describedBy }) => (
            <select id={id} className="input" value={v.project_id} onChange={pickProject} aria-invalid={invalid} aria-describedby={describedBy}>
              <option value="">Choose a project</option>
              {projectList
                .filter((p) => p.status !== 'completed')
                .map((p) => (
                  <option key={p.project_id} value={p.project_id}>
                    {p.name} · {p.client}
                  </option>
                ))}
            </select>
          )}
        </Field>
      )}
      <div className="grid grid-cols-3 gap-3">
        {input('allocation_percent', 'Allocation %', { input: { type: 'number', min: 1, max: 100, step: 5, className: 'input tnum' } })}
        {input('start_date', 'Start', { input: { type: 'date' } })}
        {input('end_date', 'End', { input: { type: 'date' } })}
      </div>
      {input('role_on_project', 'Role on the project', { field: { optional: true }, input: { maxLength: 100, placeholder: 'e.g. Lead developer' } })}
      <button type="submit" className="btn-primary" disabled={busy}>
        {busy ? <Spinner /> : <Plus size={15} aria-hidden />} Save allocation
      </button>
    </form>
  )
}

function AllocationList({ items, show, canEdit, onDelete }) {
  if (!items.length) return <p className="text-sm text-muted">No allocations yet.</p>
  return (
    <ul className="divide-y divide-line rounded-lg border border-line">
      {items.map((a) => (
        <li key={a.allocation_id} className="flex items-center justify-between gap-3 px-3 py-2.5">
          <div className="min-w-0">
            <p className="truncate text-base font-medium text-ink">
              {show === 'staff' ? a.staff_name : a.project_name}
              {a.is_current && <span className="ml-2 text-xs font-normal text-accent-ink">Now</span>}
            </p>
            <p className="truncate text-sm text-faint">
              {a.role_on_project || (show === 'staff' ? a.staff_role : 'Team member')} · {fmtDate(a.start_date)} to {fmtDate(a.end_date)}
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <span className="tnum text-base font-medium text-ink">{a.allocation_percent}%</span>
            {canEdit && (
              <button type="button" className="btn-ghost btn-sm px-1.5" onClick={() => onDelete(a)} aria-label={`Remove allocation ${a.staff_name} on ${a.project_name}`}>
                <Trash2 size={14} />
              </button>
            )}
          </div>
        </li>
      ))}
    </ul>
  )
}

/* ------------------------------------------------------------- staff tab */
const EMPTY_STAFF = { full_name: '', email: '', role_title: '', location: '', is_active: true }

function StaffPanel({ staff, projects, staffList, onClose, onChanged }) {
  const { can } = useAuth()
  const canEdit = can('resources:write')
  const toast = useToast()
  const isNew = staff && !staff.staff_id
  const [v, setV] = useState(EMPTY_STAFF)
  const [errors, setErrors] = useState({})
  const [busy, setBusy] = useState(false)
  const [allocs, setAllocs] = useState([])
  const [removing, setRemoving] = useState(null)

  useEffect(() => {
    if (!staff) return
    setV({ ...EMPTY_STAFF, ...staff, email: staff.email || '', location: staff.location || '' })
    setErrors({})
    if (staff.staff_id) api.listAllocations({ staff_id: staff.staff_id }).then(setAllocs).catch(() => setAllocs([]))
    else setAllocs([])
  }, [staff])

  const save = async (e) => {
    e.preventDefault()
    const errs = {}
    if (v.full_name.trim().length < 2) errs.full_name = 'Name must be at least 2 characters'
    if (v.role_title.trim().length < 2) errs.role_title = 'Enter a role'
    setErrors(errs)
    if (Object.keys(errs).length) return
    setBusy(true)
    const body = {
      full_name: v.full_name.trim(),
      email: v.email.trim() || null,
      role_title: v.role_title.trim(),
      location: v.location.trim() || null,
      is_active: v.is_active,
    }
    try {
      const saved = isNew ? await api.createStaff(body) : await api.updateStaff(staff.staff_id, body)
      toast.success(isNew ? 'Staff member added' : 'Staff member updated', saved.full_name)
      onChanged()
      if (isNew) onClose()
    } catch (err) {
      setErrors({ [err.field || 'full_name']: err.detail })
    } finally {
      setBusy(false)
    }
  }

  const removeAlloc = async () => {
    try {
      await api.deleteAllocation(removing.allocation_id)
      setAllocs((l) => l.filter((x) => x.allocation_id !== removing.allocation_id))
      onChanged()
    } catch (e) {
      toast.error('Could not remove the allocation', e.detail)
    } finally {
      setRemoving(null)
    }
  }

  const text = (k, label, extra = {}) => (
    <Field label={label} error={errors[k]} optional={extra.optional}>
      {({ id, invalid, describedBy }) => (
        <input id={id} className="input" value={v[k]} onChange={(e) => setV((x) => ({ ...x, [k]: e.target.value }))} aria-invalid={invalid} aria-describedby={describedBy} maxLength={extra.max || 100} />
      )}
    </Field>
  )

  return (
    <SlideOver
      open={Boolean(staff)}
      onClose={onClose}
      title={isNew ? 'Add staff member' : staff?.full_name}
      subtitle={!isNew && staff ? `${staff.role_title} · ${staff.source === 'hired' ? 'Hired through HireTrack' : 'Existing staff'}` : ''}
      width="w-[34rem]"
    >
      {staff && (
        <div className="space-y-6">
          {!isNew && (
            <div className="flex items-center justify-between rounded-lg border border-line bg-canvas px-4 py-3">
              <div>
                <p className="text-sm text-muted">Booked today</p>
                <p className="tnum text-2xl font-semibold text-ink">{staff.utilisation}%</p>
              </div>
              <p className="text-right text-sm text-muted">{BANDS[staff.band]}</p>
            </div>
          )}
          <form onSubmit={save} noValidate className="space-y-4">
            <fieldset disabled={!canEdit} className="space-y-4">
              {text('full_name', 'Full name')}
              <div className="grid grid-cols-2 gap-3">
                {text('role_title', 'Role')}
                {text('location', 'Location', { optional: true, max: 80 })}
              </div>
              {text('email', 'Email', { optional: true, max: 254 })}
              <label className="flex items-center gap-2 text-base text-ink">
                <input type="checkbox" checked={v.is_active} onChange={(e) => setV((x) => ({ ...x, is_active: e.target.checked }))} />
                Active (can be allocated)
              </label>
            </fieldset>
            {canEdit && (
              <button type="submit" className="btn-secondary" disabled={busy}>
                {busy && <Spinner />} {isNew ? 'Add staff member' : 'Save details'}
              </button>
            )}
          </form>
          {!isNew && (
            <section className="space-y-3 border-t border-line pt-5">
              <h3 className="text-sm font-semibold text-ink">Allocations</h3>
              <AllocationList items={allocs} show="project" canEdit={canEdit} onDelete={setRemoving} />
              {canEdit && staff.is_active && (
                <AllocationForm
                  fixedStaff={staff}
                  projectList={projects}
                  staffList={staffList}
                  onSaved={(a) => {
                    setAllocs((l) => [a, ...l])
                    onChanged()
                  }}
                />
              )}
            </section>
          )}
        </div>
      )}
      <ConfirmDialog
        open={Boolean(removing)}
        title="Remove this allocation?"
        confirmLabel="Remove"
        onConfirm={removeAlloc}
        onCancel={() => setRemoving(null)}
      >
        {removing && `${removing.staff_name} will no longer be booked on ${removing.project_name}.`}
      </ConfirmDialog>
    </SlideOver>
  )
}

function StaffTab({ staff, projects, reload }) {
  const { can } = useAuth()
  const [params, setParams] = useSearchParams()
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(null)
  const band = params.get('band') || ''
  const dq = useDebounced(query, 120)

  const rows = useMemo(() => {
    if (!staff) return []
    const t = dq.trim().toLowerCase()
    return staff.filter(
      (s) =>
        (!band || s.band === band) &&
        (!t || s.full_name.toLowerCase().includes(t) || s.role_title.toLowerCase().includes(t) || s.current_projects.some((p) => p.toLowerCase().includes(t))),
    )
  }, [staff, band, dq])

  const active = (staff || []).filter((s) => s.is_active)
  const avg = active.length ? Math.round(active.reduce((n, s) => n + s.utilisation, 0) / active.length) : 0

  return (
    <>
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div className="relative w-full max-w-xs">
          <Search size={15} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-faint" aria-hidden />
          <input type="search" className="input pl-9" placeholder="Name, role or project" aria-label="Search staff" value={query} onChange={(e) => setQuery(e.target.value)} />
        </div>
        <select
          className="input w-52"
          aria-label="Utilisation"
          value={band}
          onChange={(e) => setParams(e.target.value ? { band: e.target.value } : {})}
        >
          <option value="">All utilisation</option>
          {Object.entries(BANDS).map(([k, l]) => (
            <option key={k} value={k}>
              {l}
            </option>
          ))}
        </select>
        {staff && (
          <span className="tnum text-sm text-muted">
            {active.length} active · average {avg}% booked today · {active.filter((s) => s.band === 'bench').length} on the bench
          </span>
        )}
        {can('resources:write') && (
          <button type="button" className="btn-primary ml-auto" onClick={() => setOpen({ ...EMPTY_STAFF })}>
            <Plus size={16} aria-hidden /> Add staff member
          </button>
        )}
      </div>

      <div className="panel overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[48rem] text-left">
            <thead className="border-b border-line bg-canvas">
              <tr>
                <th className="th px-4 py-2.5">Name</th>
                <th className="th px-4 py-2.5">Role</th>
                <th className="th px-4 py-2.5">Source</th>
                <th className="th px-4 py-2.5">Booked today</th>
                <th className="th px-4 py-2.5">Current projects</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {staff === null
                ? [0, 1, 2, 3, 4].map((i) => (
                    <tr key={i}>
                      <td colSpan={5} className="px-4 py-3">
                        <Skeleton className="h-5 w-full" />
                      </td>
                    </tr>
                  ))
                : rows.map((s) => (
                    <tr key={s.staff_id} className="cursor-pointer hover:bg-canvas" onClick={() => setOpen(s)}>
                      <td className="px-4 py-2.5">
                        <button type="button" className="text-left" onClick={() => setOpen(s)}>
                          <span className="block text-base font-medium text-ink">{s.full_name}</span>
                          <span className="block text-sm text-faint">{s.location || '–'}</span>
                        </button>
                      </td>
                      <td className="px-4 py-2.5 text-sm text-muted">{s.role_title}</td>
                      <td className="px-4 py-2.5 text-sm text-muted">{s.source === 'hired' ? 'Hired' : 'Existing'}</td>
                      <td className="px-4 py-2.5">{s.is_active ? <Utilisation value={s.utilisation} /> : <span className="text-sm text-faint">Inactive</span>}</td>
                      <td className="max-w-[18rem] truncate px-4 py-2.5 text-sm text-muted">{s.current_projects.join(', ') || '–'}</td>
                    </tr>
                  ))}
            </tbody>
          </table>
          {staff && rows.length === 0 && (
            <EmptyState icon={Users} title={staff.length ? 'Nobody matches these filters' : 'No staff yet'}>
              {staff.length ? 'Clear the search or choose a different utilisation band.' : 'People hired through the pipeline are added here automatically.'}
            </EmptyState>
          )}
        </div>
      </div>

      <StaffPanel
        staff={open}
        projects={projects || []}
        staffList={staff || []}
        onClose={() => setOpen(null)}
        onChanged={async () => {
          const fresh = await reload()
          setOpen((o) => (o && o.staff_id ? fresh.find((x) => x.staff_id === o.staff_id) || null : o))
        }}
      />
    </>
  )
}

/* ---------------------------------------------------------- projects tab */
const EMPTY_PROJECT = { name: '', client: '', description: '', start_date: '', end_date: '', status: 'planned' }

function ProjectPanel({ project, staffList, onClose, onChanged }) {
  const { can } = useAuth()
  const canEdit = can('resources:write')
  const toast = useToast()
  const isNew = project && !project.project_id
  const [v, setV] = useState(EMPTY_PROJECT)
  const [detail, setDetail] = useState(null)
  const [errors, setErrors] = useState({})
  const [busy, setBusy] = useState(false)
  const [removing, setRemoving] = useState(null)
  const [confirmDelete, setConfirmDelete] = useState(false)

  const loadDetail = useCallback((pid) => api.getProject(pid).then(setDetail), [])
  useEffect(() => {
    if (!project) return
    setV({ ...EMPTY_PROJECT, ...project, description: project.description || '' })
    setErrors({})
    setDetail(null)
    if (project.project_id) loadDetail(project.project_id).catch(() => {})
  }, [project, loadDetail])

  const save = async (e) => {
    e.preventDefault()
    const errs = {}
    if (v.name.trim().length < 2) errs.name = 'Name must be at least 2 characters'
    if (v.client.trim().length < 2) errs.client = 'Enter the client'
    if (!v.start_date) errs.start_date = 'Choose a start date'
    if (!v.end_date) errs.end_date = 'Choose an end date'
    else if (v.start_date && v.end_date < v.start_date) errs.end_date = 'End date cannot be before the start date'
    setErrors(errs)
    if (Object.keys(errs).length) return
    setBusy(true)
    const body = {
      name: v.name.trim(),
      client: v.client.trim(),
      description: v.description.trim() || null,
      start_date: v.start_date,
      end_date: v.end_date,
      status: v.status,
    }
    try {
      const saved = isNew ? await api.createProject(body) : await api.updateProject(project.project_id, body)
      toast.success(isNew ? 'Project created' : 'Project updated', saved.name)
      setDetail(saved)
      onChanged(saved)
    } catch (err) {
      setErrors({ [err.field || 'name']: err.detail })
    } finally {
      setBusy(false)
    }
  }

  const removeAlloc = async () => {
    try {
      await api.deleteAllocation(removing.allocation_id)
      await loadDetail(project.project_id)
      onChanged()
    } catch (e) {
      toast.error('Could not remove the allocation', e.detail)
    } finally {
      setRemoving(null)
    }
  }

  const deleteProject = async () => {
    try {
      await api.deleteProject(project.project_id)
      toast.success('Project deleted', project.name)
      setConfirmDelete(false)
      onChanged()
      onClose()
    } catch (e) {
      toast.error('Could not delete the project', e.detail)
    }
  }

  const field = (k, label, props = {}) => (
    <Field label={label} error={errors[k]} optional={props.optional}>
      {({ id, invalid, describedBy }) =>
        props.textarea ? (
          <textarea id={id} rows={3} className="input" value={v[k]} onChange={(e) => setV((x) => ({ ...x, [k]: e.target.value }))} aria-describedby={describedBy} maxLength={2000} />
        ) : (
          <input id={id} className="input" value={v[k]} onChange={(e) => setV((x) => ({ ...x, [k]: e.target.value }))} aria-invalid={invalid} aria-describedby={describedBy} {...(props.input || {})} />
        )
      }
    </Field>
  )

  const current = project?.project_id ? detail || project : null
  return (
    <SlideOver
      open={Boolean(project)}
      onClose={onClose}
      title={isNew ? 'New project' : project?.name}
      subtitle={!isNew && project ? project.client : ''}
      width="w-[38rem]"
    >
      {project && (
        <div className="space-y-6">
          <form onSubmit={save} noValidate className="space-y-4">
            <fieldset disabled={!canEdit} className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                {field('name', 'Project name', { input: { maxLength: 100 } })}
                {field('client', 'Client', { input: { maxLength: 100 } })}
              </div>
              <div className="grid grid-cols-3 gap-3">
                {field('start_date', 'Start', { input: { type: 'date' } })}
                {field('end_date', 'End', { input: { type: 'date' } })}
                <Field label="Status">
                  {({ id }) => (
                    <select id={id} className="input" value={v.status} onChange={(e) => setV((x) => ({ ...x, status: e.target.value }))}>
                      {Object.entries(PROJECT_STATUS).map(([k, l]) => (
                        <option key={k} value={k}>
                          {l}
                        </option>
                      ))}
                    </select>
                  )}
                </Field>
              </div>
              {field('description', 'Description', { optional: true, textarea: true })}
            </fieldset>
            {canEdit && (
              <div className="flex items-center gap-2">
                <button type="submit" className="btn-secondary" disabled={busy}>
                  {busy && <Spinner />} {isNew ? 'Create project' : 'Save details'}
                </button>
                {!isNew && (
                  <button type="button" className="btn-danger-ghost ml-auto" onClick={() => setConfirmDelete(true)}>
                    <Trash2 size={15} aria-hidden /> Delete project
                  </button>
                )}
              </div>
            )}
          </form>

          {current && (
            <section className="space-y-3 border-t border-line pt-5">
              <div className="flex items-baseline justify-between">
                <h3 className="text-sm font-semibold text-ink">Team</h3>
                <span className="tnum text-sm text-muted">
                  {current.team_size} {current.team_size === 1 ? 'person' : 'people'} · {(current.allocated_percent / 100).toFixed(1)} full-time equivalent today
                </span>
              </div>
              {detail ? (
                <AllocationList items={detail.allocations || []} show="staff" canEdit={canEdit} onDelete={setRemoving} />
              ) : (
                <Skeleton className="h-20 w-full" />
              )}
              {canEdit && detail && detail.status !== 'completed' && (
                <AllocationForm
                  key={detail.project_id}
                  fixedProject={detail}
                  staffList={staffList}
                  projectList={[]}
                  onSaved={async () => {
                    await loadDetail(project.project_id)
                    onChanged()
                  }}
                />
              )}
              {detail && detail.status === 'completed' && <p className="text-sm text-faint">This project is completed, so no new allocations can be added.</p>}
            </section>
          )}
        </div>
      )}
      <ConfirmDialog open={Boolean(removing)} title="Remove this allocation?" confirmLabel="Remove" onConfirm={removeAlloc} onCancel={() => setRemoving(null)}>
        {removing && `${removing.staff_name} will no longer be booked on ${removing.project_name}.`}
      </ConfirmDialog>
      <ConfirmDialog
        open={confirmDelete}
        title={`Delete ${project?.name}?`}
        confirmLabel="Delete project"
        onConfirm={deleteProject}
        onCancel={() => setConfirmDelete(false)}
      >
        The project and all of its allocations will be removed. Staff become free for those dates.
      </ConfirmDialog>
    </SlideOver>
  )
}

function ProjectsTab({ projects, staff, reloadAll }) {
  const { can } = useAuth()
  const [status, setStatus] = useState('')
  const [open, setOpen] = useState(null)
  const rows = (projects || []).filter((p) => !status || p.status === status)
  return (
    <>
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <select className="input w-48" aria-label="Project status" value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">All statuses</option>
          {Object.entries(PROJECT_STATUS).map(([k, l]) => (
            <option key={k} value={k}>
              {l}
            </option>
          ))}
        </select>
        {projects && <span className="text-sm text-muted">{rows.length} projects</span>}
        {can('resources:write') && (
          <button type="button" className="btn-primary ml-auto" onClick={() => setOpen({ ...EMPTY_PROJECT })}>
            <Plus size={16} aria-hidden /> New project
          </button>
        )}
      </div>
      <div className="panel overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[48rem] text-left">
            <thead className="border-b border-line bg-canvas">
              <tr>
                <th className="th px-4 py-2.5">Project</th>
                <th className="th px-4 py-2.5">Status</th>
                <th className="th px-4 py-2.5">Dates</th>
                <th className="th px-4 py-2.5 text-right">Team</th>
                <th className="th px-4 py-2.5 text-right" title="Full-time equivalent: the sum of today's allocations / 100">FTE today</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {projects === null
                ? [0, 1, 2].map((i) => (
                    <tr key={i}>
                      <td colSpan={5} className="px-4 py-3">
                        <Skeleton className="h-5 w-full" />
                      </td>
                    </tr>
                  ))
                : rows.map((p) => (
                    <tr key={p.project_id} className="cursor-pointer hover:bg-canvas" onClick={() => setOpen(p)}>
                      <td className="px-4 py-2.5">
                        <button type="button" className="text-left" onClick={() => setOpen(p)}>
                          <span className="block text-base font-medium text-ink">{p.name}</span>
                          <span className="block text-sm text-faint">{p.client}</span>
                        </button>
                      </td>
                      <td className="px-4 py-2.5">
                        <StatusChip status={p.status} />
                      </td>
                      <td className="tnum px-4 py-2.5 text-sm text-muted">
                        {fmtDate(p.start_date)} to {fmtDate(p.end_date)}
                      </td>
                      <td className="tnum px-4 py-2.5 text-right text-base text-ink">{p.team_size}</td>
                      <td className="tnum px-4 py-2.5 text-right text-sm text-muted">{p.allocated_percent ? (p.allocated_percent / 100).toFixed(1) : '–'}</td>
                    </tr>
                  ))}
            </tbody>
          </table>
          {projects && rows.length === 0 && (
            <EmptyState icon={FolderKanban} title="No projects">
              {projects.length ? 'No project has this status.' : 'Create a project, then allocate staff to it.'}
            </EmptyState>
          )}
        </div>
      </div>
      <ProjectPanel
        project={open}
        staffList={staff || []}
        onClose={() => setOpen(null)}
        onChanged={(saved) => {
          reloadAll()
          if (saved && saved.project_id) setOpen((o) => (o && !o.project_id ? saved : o))
        }}
      />
    </>
  )
}

export default function Resources() {
  const { tab } = useParams()
  const toast = useToast()
  const [staff, setStaff] = useState(null)
  const [projects, setProjects] = useState(null)
  const current = tab === 'projects' ? 'projects' : 'staff'

  const loadStaff = useCallback(
    () =>
      api
        .listStaff()
        .then((s) => {
          setStaff(s)
          return s
        })
        .catch((e) => {
          toast.error('Could not load staff', e.detail)
          setStaff([])
          return []
        }),
    [toast],
  )
  const loadProjects = useCallback(() => api.listProjects().then(setProjects).catch(() => setProjects([])), [])
  useEffect(() => {
    loadStaff()
    loadProjects()
  }, [loadStaff, loadProjects])

  const tabClass = ({ isActive }) =>
    `relative flex items-center gap-2 px-1 pb-2.5 text-base font-medium ${isActive ? 'text-ink after:absolute after:inset-x-0 after:-bottom-px after:h-0.5 after:rounded-full after:bg-accent' : 'text-muted hover:text-ink'}`

  return (
    <div>
      <PageHeader title="Resource allocation" description="Who is available, who is booked, and where." />
      <nav aria-label="Resources" className="mb-5 flex gap-6 border-b border-line">
        <NavLink to="/resources" end className={tabClass}>
          <Users size={15} aria-hidden /> Staff {staff && <span className="tnum text-sm text-faint">{staff.length}</span>}
        </NavLink>
        <NavLink to="/resources/projects" className={tabClass}>
          <Briefcase size={15} aria-hidden /> Projects {projects && <span className="tnum text-sm text-faint">{projects.length}</span>}
        </NavLink>
      </nav>
      {current === 'staff' ? (
        <StaffTab
          staff={staff}
          projects={projects}
          reload={async () => {
            loadProjects()
            return loadStaff()
          }}
        />
      ) : (
        <ProjectsTab
          projects={projects}
          staff={staff}
          reloadAll={() => {
            loadProjects()
            loadStaff()
          }}
        />
      )}
    </div>
  )
}
