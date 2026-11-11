import { Database, HardDriveDownload, History, Pencil, RotateCcw, UserPlus, UsersRound } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { api } from '../apiClient'
import { ConfirmDialog, SlideOver } from '../components/Overlay'
import { useToast } from '../components/Toast'
import { Field, PageHeader, Skeleton, Spinner } from '../components/ui'
import { ROLE_LABELS, useAuth } from '../lib/auth'
import { bytes, dateTime, timeAgo } from '../lib/format'

function ActionRow({ icon: Icon, title, children, action }) {
  return (
    <div className="flex flex-wrap items-center gap-4 px-5 py-4">
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-line bg-canvas text-muted">
        <Icon size={17} strokeWidth={1.75} aria-hidden />
      </div>
      <div className="min-w-0 flex-1">
        <h3 className="text-base font-medium text-ink">{title}</h3>
        <p className="text-sm text-muted">{children}</p>
      </div>
      {action}
    </div>
  )
}

/* ------------------------------------------------------------------ users */
const EMPTY_USER = { full_name: '', email: '', role: 'recruiter', password: '', is_active: true }

function UserPanel({ user, onClose, onSaved }) {
  const toast = useToast()
  const isNew = user && !user.user_id
  const [v, setV] = useState(EMPTY_USER)
  const [errors, setErrors] = useState({})
  const [busy, setBusy] = useState(false)
  useEffect(() => {
    if (user) {
      setV({ ...EMPTY_USER, ...user, password: '' })
      setErrors({})
    }
  }, [user])
  const set = (k) => (e) => setV((x) => ({ ...x, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value }))

  const save = async (e) => {
    e.preventDefault()
    const errs = {}
    if (v.full_name.trim().length < 2) errs.full_name = 'Name must be at least 2 characters'
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(v.email.trim())) errs.email = 'Enter a valid email address'
    if ((isNew || v.password) && (v.password.length < 8 || !/[A-Za-z]/.test(v.password) || !/[0-9]/.test(v.password)))
      errs.password = 'At least 8 characters, with a letter and a number'
    setErrors(errs)
    if (Object.keys(errs).length) return
    setBusy(true)
    const body = { full_name: v.full_name.trim(), email: v.email.trim(), role: v.role, is_active: v.is_active, password: v.password || null }
    try {
      const saved = isNew ? await api.createUser(body) : await api.updateUser(user.user_id, body)
      toast.success(isNew ? 'User created' : 'User updated', saved.email)
      onSaved()
      onClose()
    } catch (err) {
      setErrors({ [err.field || 'full_name']: err.detail })
    } finally {
      setBusy(false)
    }
  }

  return (
    <SlideOver
      open={Boolean(user)}
      onClose={onClose}
      title={isNew ? 'Add user' : 'Edit user'}
      subtitle={!isNew && user ? user.email : 'They sign in with this email and password.'}
      width="w-[28rem]"
      footer={
        <>
          <button type="submit" form="user-form" className="btn-primary" disabled={busy}>
            {busy && <Spinner />} {isNew ? 'Create user' : 'Save changes'}
          </button>
          <button type="button" className="btn-ghost" onClick={onClose}>
            Cancel
          </button>
        </>
      }
    >
      <form id="user-form" onSubmit={save} noValidate className="space-y-4">
        <Field label="Full name" error={errors.full_name}>
          {({ id, invalid, describedBy }) => <input id={id} className="input" value={v.full_name} onChange={set('full_name')} aria-invalid={invalid} aria-describedby={describedBy} maxLength={100} />}
        </Field>
        <Field label="Email" error={errors.email}>
          {({ id, invalid, describedBy }) => <input id={id} type="email" className="input" value={v.email} onChange={set('email')} aria-invalid={invalid} aria-describedby={describedBy} autoComplete="off" />}
        </Field>
        <Field label="Role" error={errors.role} hint="Recruiters manage candidates, jobs, matching and the pipeline. Resource managers manage staff and projects.">
          {({ id, describedBy }) => (
            <select id={id} className="input" value={v.role} onChange={set('role')} aria-describedby={describedBy}>
              {Object.entries(ROLE_LABELS).map(([k, l]) => (
                <option key={k} value={k}>
                  {l}
                </option>
              ))}
            </select>
          )}
        </Field>
        <Field label={isNew ? 'Password' : 'New password'} optional={!isNew} error={errors.password} hint={isNew ? 'At least 8 characters, with a letter and a number.' : 'Leave blank to keep the current password.'}>
          {({ id, invalid, describedBy }) => (
            <input id={id} type="password" className="input" value={v.password} onChange={set('password')} aria-invalid={invalid} aria-describedby={describedBy} autoComplete="new-password" />
          )}
        </Field>
        <label className="flex items-center gap-2 text-base text-ink">
          <input type="checkbox" checked={v.is_active} onChange={set('is_active')} /> Account is active
        </label>
        {errors.is_active && <p className="text-sm text-danger">{errors.is_active}</p>}
      </form>
    </SlideOver>
  )
}

/* ------------------------------------------------------------------- page */
const CONFIRMS = {
  seed: {
    title: 'Replace all data with the small demo set?',
    body: 'Candidates, jobs, applications, staff and projects are replaced with 18 candidates and 3 jobs. User accounts are kept. A safety backup is taken first.',
  },
  'seed-full': {
    title: 'Load the full seed dataset?',
    body: 'All current data is replaced with 600 candidates, 33 jobs, about 900 applications, staff and 12 projects. User accounts are kept. A safety backup is taken first.',
  },
  'seed-large': {
    title: 'Load the large dataset?',
    body: 'The full dataset plus 2,000 extra generated candidates, to test speed at scale. A safety backup is taken first. The first match afterwards reads every new CV once.',
  },
  restore: {
    title: 'Restore this backup?',
    body: 'The database returns to how it was when the backup was taken. Your current data is backed up first, and the backup is integrity-checked before anything changes.',
  },
}

export default function Admin() {
  const toast = useToast()
  const { user: me } = useAuth()
  const [users, setUsers] = useState(null)
  const [editing, setEditing] = useState(null)
  const [backups, setBackups] = useState(null)
  const [busy, setBusy] = useState(null)
  const [confirm, setConfirm] = useState(null) // {kind, file?, created?}
  const [password, setPassword] = useState('')
  const [pwError, setPwError] = useState('')

  const loadUsers = useCallback(() => api.listUsers().then(setUsers).catch(() => setUsers([])), [])
  const loadBackups = useCallback(() => api.listBackups().then(setBackups).catch(() => setBackups([])), [])
  useEffect(() => {
    loadUsers()
    loadBackups()
  }, [loadUsers, loadBackups])

  const closeConfirm = () => {
    setConfirm(null)
    setPassword('')
    setPwError('')
  }

  const backupNow = async () => {
    setBusy('backup')
    try {
      const b = await api.backupNow()
      toast.success('Backup created', b.file)
      loadBackups()
    } catch (err) {
      toast.error('Backup failed', err.detail)
    } finally {
      setBusy(null)
    }
  }

  // Destructive actions: the admin's own password is sent again with the request.
  const runConfirmed = async () => {
    if (!password) {
      setPwError('Enter your password to confirm')
      return
    }
    const kind = confirm.kind
    setBusy(kind)
    try {
      if (kind === 'seed') {
        const r = await api.seed(password)
        toast.success('Demo data loaded', `${r.candidates} candidates and ${r.jobs} jobs.`)
      } else if (kind === 'seed-full') {
        const r = await api.seedFull(password)
        toast.success('Full dataset loaded', `${r.candidates} candidates, ${r.jobs} jobs, ${r.applications} applications, ${r.projects} projects.`)
      } else if (kind === 'seed-large') {
        const r = await api.seedLarge(password)
        toast.success('Large dataset loaded', `${r.candidates.toLocaleString()} candidates. CVs are being prepared in the background.`)
      } else if (kind === 'restore') {
        const r = await api.restoreBackup(confirm.file, password)
        toast.success('Backup restored', `Your previous data was saved first as ${r.safety_backup}.`)
        loadUsers()
      }
      closeConfirm()
      loadBackups()
    } catch (err) {
      if (err.field === 'password') setPwError(err.detail)
      else {
        toast.error('That did not work', err.detail)
        closeConfirm()
      }
    } finally {
      setBusy(null)
    }
  }

  return (
    <div className="max-w-5xl space-y-6">
      <PageHeader title="Administration" description="User accounts, seed data and backups." />

      <section className="panel">
        <div className="flex items-center justify-between gap-3 border-b border-line px-5 py-3">
          <div>
            <h2 className="text-md font-semibold text-ink">Users</h2>
            <p className="text-sm text-muted">Each person signs in with their own account. The role decides what they can see and change.</p>
          </div>
          <button type="button" className="btn-primary" onClick={() => setEditing({ ...EMPTY_USER })}>
            <UserPlus size={15} aria-hidden /> Add user
          </button>
        </div>
        {users === null ? (
          <div className="space-y-2 p-5">
            {[0, 1, 2].map((i) => (
              <Skeleton key={i} className="h-9 w-full" />
            ))}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[40rem] text-left">
              <thead>
                <tr className="border-b border-line bg-canvas">
                  <th className="th px-5 py-2.5">Name</th>
                  <th className="th px-5 py-2.5">Role</th>
                  <th className="th px-5 py-2.5">Status</th>
                  <th className="th px-5 py-2.5">Last sign-in</th>
                  <th className="px-5 py-2.5">
                    <span className="sr-only">Actions</span>
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {users.map((u) => (
                  <tr key={u.user_id}>
                    <td className="px-5 py-2.5">
                      <span className="block text-base font-medium text-ink">
                        {u.full_name}
                        {u.user_id === me.user_id && <span className="ml-2 text-xs font-normal text-faint">You</span>}
                      </span>
                      <span className="block text-sm text-faint">{u.email}</span>
                    </td>
                    <td className="px-5 py-2.5 text-sm text-muted">{ROLE_LABELS[u.role]}</td>
                    <td className="px-5 py-2.5 text-sm">{u.is_active ? <span className="text-ink">Active</span> : <span className="text-faint">Deactivated</span>}</td>
                    <td className="px-5 py-2.5 text-sm text-muted">{u.last_login_at ? timeAgo(u.last_login_at) : 'Never'}</td>
                    <td className="px-5 py-2.5 text-right">
                      <button type="button" className="btn-ghost btn-sm" onClick={() => setEditing(u)} aria-label={`Edit ${u.full_name}`}>
                        <Pencil size={14} aria-hidden /> Edit
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="panel divide-y divide-line">
        <div className="px-5 py-3">
          <h2 className="text-md font-semibold text-ink">Data</h2>
          <p className="text-sm text-muted">Each option replaces the current data. You will be asked for your password.</p>
        </div>
        <ActionRow
          icon={Database}
          title="Full seed dataset"
          action={
            <button type="button" className="btn-secondary" onClick={() => setConfirm({ kind: 'seed-full' })}>
              Load full dataset
            </button>
          }
        >
          600 candidates, 33 jobs, applications at every stage, staff, projects and allocations.
        </ActionRow>
        <ActionRow
          icon={Database}
          title="Small demo set"
          action={
            <button type="button" className="btn-secondary" onClick={() => setConfirm({ kind: 'seed' })}>
              Load demo set
            </button>
          }
        >
          18 hand-written candidates and 3 jobs, used by the guided matching demo.
        </ActionRow>
        <ActionRow
          icon={UsersRound}
          title="Large dataset"
          action={
            <button type="button" className="btn-secondary" onClick={() => setConfirm({ kind: 'seed-large' })}>
              Load 2,600 candidates
            </button>
          }
        >
          The full dataset plus 2,000 generated candidates, to show matching speed at scale.
        </ActionRow>
      </section>

      <section className="panel">
        <div className="flex items-center justify-between gap-3 border-b border-line px-5 py-3">
          <div>
            <h2 className="text-md font-semibold text-ink">Backups</h2>
            <p className="text-sm text-muted">Taken daily at start-up and before every load or restore. The 10 most recent are kept.</p>
          </div>
          <button type="button" className="btn-primary" onClick={backupNow} disabled={busy === 'backup'}>
            {busy === 'backup' ? <Spinner /> : <HardDriveDownload size={15} aria-hidden />} Back up now
          </button>
        </div>
        {backups === null ? (
          <div className="space-y-2 p-5">
            {[0, 1, 2].map((i) => (
              <Skeleton key={i} className="h-9 w-full" />
            ))}
          </div>
        ) : backups.length === 0 ? (
          <div className="flex items-center gap-3 px-5 py-6 text-sm text-muted">
            <History size={16} aria-hidden /> No backups yet. Press Back up now to create the first one.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[36rem] text-left">
              <thead>
                <tr className="border-b border-line bg-canvas">
                  <th className="th px-5 py-2.5">Created</th>
                  <th className="th px-5 py-2.5">Reason</th>
                  <th className="th px-5 py-2.5 text-right">Size</th>
                  <th className="px-5 py-2.5">
                    <span className="sr-only">Actions</span>
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {backups.map((b) => (
                  <tr key={b.file}>
                    <td className="px-5 py-2.5">
                      <span className="block text-base text-ink">{dateTime(b.created_at)}</span>
                      <span className="block font-mono text-2xs text-faint">{b.file}</span>
                    </td>
                    <td className="px-5 py-2.5 text-sm text-muted">{b.reason}</td>
                    <td className="tnum px-5 py-2.5 text-right text-sm text-muted">{bytes(b.size_bytes)}</td>
                    <td className="px-5 py-2.5 text-right">
                      <button type="button" className="btn-secondary btn-sm" onClick={() => setConfirm({ kind: 'restore', file: b.file, created: b.created_at })}>
                        <RotateCcw size={13} aria-hidden /> Restore
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <ConfirmDialog
        open={Boolean(confirm)}
        title={confirm ? CONFIRMS[confirm.kind].title : ''}
        confirmLabel={confirm?.kind === 'restore' ? 'Restore backup' : 'Replace data'}
        busy={busy && busy !== 'backup'}
        onConfirm={runConfirmed}
        onCancel={closeConfirm}
      >
        <p>
          {confirm ? CONFIRMS[confirm.kind].body : ''}
          {confirm?.kind === 'restore' && confirm.created ? ` Backup taken ${timeAgo(confirm.created)}.` : ''}
        </p>
        <Field label="Your password" error={pwError} className="mt-4">
          {({ id, invalid, describedBy }) => (
            <input
              id={id}
              type="password"
              className="input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && runConfirmed()}
              aria-invalid={invalid}
              aria-describedby={describedBy}
              autoComplete="current-password"
            />
          )}
        </Field>
      </ConfirmDialog>

      <UserPanel user={editing} onClose={() => setEditing(null)} onSaved={loadUsers} />
    </div>
  )
}
