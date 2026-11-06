import { Database, HardDriveDownload, History, KeyRound, Lock, RotateCcw, Unlock, UsersRound } from 'lucide-react'
import { useCallback, useState } from 'react'
import { api } from '../apiClient'
import { ConfirmDialog } from '../components/Overlay'
import { useToast } from '../components/Toast'
import { Field, PageHeader, Skeleton, Spinner } from '../components/ui'
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

export default function Admin() {
  const toast = useToast()
  // The passcode lives only in memory for this page visit; it is never stored.
  const [passcode, setPasscode] = useState('')
  const [unlocked, setUnlocked] = useState(false)
  const [error, setError] = useState('')
  const [checking, setChecking] = useState(false)
  const [backups, setBackups] = useState(null)
  const [busy, setBusy] = useState(null)
  const [confirm, setConfirm] = useState(null) // {kind, file?}
  const [restorePass, setRestorePass] = useState('')
  const [restoreError, setRestoreError] = useState('')

  const loadBackups = useCallback((code) => api.listBackups(code).then(setBackups).catch(() => setBackups([])), [])

  const unlock = async (e) => {
    e.preventDefault()
    if (!passcode) {
      setError('Enter the admin passcode')
      return
    }
    setChecking(true)
    try {
      await api.verifyPasscode(passcode)
      setUnlocked(true)
      setError('')
      loadBackups(passcode)
    } catch (err) {
      setError(err.detail)
    } finally {
      setChecking(false)
    }
  }

  const lock = () => {
    setUnlocked(false)
    setPasscode('')
    setBackups(null)
  }

  const run = async (kind) => {
    setBusy(kind)
    try {
      if (kind === 'seed') {
        const r = await api.seed(passcode)
        toast.success('Demo data loaded', `${r.candidates} candidates and ${r.jobs} jobs. A safety backup was taken first.`)
      } else if (kind === 'seed-large') {
        const r = await api.seedLarge(passcode)
        toast.success('Large dataset loaded', `${r.candidates.toLocaleString()} candidates. CV meanings are being prepared in the background.`)
      } else if (kind === 'backup') {
        const b = await api.backupNow(passcode)
        toast.success('Backup created', b.file)
      } else if (kind === 'restore') {
        if (restorePass !== passcode) {
          setRestoreError('Passcode does not match')
          setBusy(null)
          return
        }
        const r = await api.restoreBackup(confirm.file, restorePass)
        toast.success('Backup restored', `Your previous data was saved first as ${r.safety_backup}.`)
      }
      setConfirm(null)
      setRestorePass('')
      setRestoreError('')
      loadBackups(passcode)
    } catch (err) {
      if (err.status === 401) {
        toast.error('Passcode rejected', 'Unlock the admin tools again.')
        lock()
        setConfirm(null)
      } else toast.error('That did not work', err.detail)
    } finally {
      setBusy(null)
    }
  }

  return (
    <div className="max-w-4xl">
      <PageHeader title="Admin" description="Demo data, backups and restore. Every action needs the admin passcode." />

      <section className="panel mb-6">
        <form onSubmit={unlock} className="flex flex-wrap items-end gap-3 px-5 py-4">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center self-center rounded-lg border border-line bg-canvas text-muted">
            {unlocked ? <Unlock size={17} strokeWidth={1.75} aria-hidden /> : <Lock size={17} strokeWidth={1.75} aria-hidden />}
          </div>
          {unlocked ? (
            <>
              <div className="flex-1">
                <p className="text-base font-medium text-ink">Admin tools unlocked</p>
                <p className="text-sm text-muted">The passcode is kept only until you leave this page.</p>
              </div>
              <button type="button" className="btn-secondary" onClick={lock}>
                <Lock size={15} aria-hidden /> Lock
              </button>
            </>
          ) : (
            <>
              <Field label="Admin passcode" error={error} className="min-w-[16rem] flex-1">
                {({ id, invalid, describedBy }) => (
                  <input
                    id={id}
                    type="password"
                    autoComplete="current-password"
                    className="input"
                    value={passcode}
                    onChange={(e) => setPasscode(e.target.value)}
                    aria-invalid={invalid}
                    aria-describedby={describedBy}
                  />
                )}
              </Field>
              <button type="submit" className="btn-primary" disabled={checking}>
                {checking ? <Spinner /> : <KeyRound size={15} aria-hidden />} Unlock
              </button>
            </>
          )}
        </form>
      </section>

      <fieldset disabled={!unlocked} className={`space-y-6 transition-opacity ${unlocked ? '' : 'opacity-50'}`}>
        <section className="panel divide-y divide-line">
          <h2 className="px-5 py-3 text-md font-semibold text-ink">Demo data</h2>
          <ActionRow
            icon={Database}
            title="Load or reset demo data"
            action={
              <button type="button" className="btn-secondary" onClick={() => setConfirm({ kind: 'seed' })}>
                Load demo data
              </button>
            }
          >
            Replaces everything with 18 sample candidates and 3 job specifications.
          </ActionRow>
          <ActionRow
            icon={UsersRound}
            title="Load large demo dataset"
            action={
              <button type="button" className="btn-secondary" onClick={() => setConfirm({ kind: 'seed-large' })}>
                Load 2,000 candidates
              </button>
            }
          >
            The demo data plus about 2,000 generated IT candidates, to show speed at scale.
          </ActionRow>
        </section>

        <section className="panel">
          <div className="flex items-center justify-between border-b border-line px-5 py-3">
            <div>
              <h2 className="text-md font-semibold text-ink">Backups</h2>
              <p className="text-sm text-muted">Taken daily at start-up and before every load or restore. The 10 most recent are kept.</p>
            </div>
            <button type="button" className="btn-primary" onClick={() => run('backup')} disabled={busy === 'backup'}>
              {busy === 'backup' ? <Spinner /> : <HardDriveDownload size={15} aria-hidden />} Back up now
            </button>
          </div>
          {!unlocked ? (
            <p className="px-5 py-6 text-sm text-muted">Unlock to see backups.</p>
          ) : backups === null ? (
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
            <table className="w-full">
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
          )}
        </section>
      </fieldset>

      <ConfirmDialog
        open={confirm?.kind === 'seed'}
        title="Replace all data with the demo set?"
        confirmLabel="Replace data"
        busy={busy === 'seed'}
        onConfirm={() => run('seed')}
        onCancel={() => setConfirm(null)}
      >
        All current candidates, jobs and results will be replaced. A safety backup is taken first, so you can restore it.
      </ConfirmDialog>
      <ConfirmDialog
        open={confirm?.kind === 'seed-large'}
        title="Load the large demo dataset?"
        confirmLabel="Replace data"
        busy={busy === 'seed-large'}
        onConfirm={() => run('seed-large')}
        onCancel={() => setConfirm(null)}
      >
        All current data will be replaced with about 2,000 candidates. A safety backup is taken first. Loading takes a few seconds.
      </ConfirmDialog>
      <ConfirmDialog
        open={confirm?.kind === 'restore'}
        title="Restore this backup?"
        confirmLabel="Restore backup"
        busy={busy === 'restore'}
        confirmDisabled={!restorePass}
        onConfirm={() => run('restore')}
        onCancel={() => {
          setConfirm(null)
          setRestorePass('')
          setRestoreError('')
        }}
      >
        <p>
          The database will be returned to how it was {confirm?.created ? timeAgo(confirm.created) : ''}. Your current data is backed up first. The backup is
          integrity-checked before anything changes.
        </p>
        <Field label="Re-enter the admin passcode to confirm" error={restoreError} className="mt-4">
          {({ id, invalid, describedBy }) => (
            <input
              id={id}
              type="password"
              className="input"
              value={restorePass}
              onChange={(e) => setRestorePass(e.target.value)}
              aria-invalid={invalid}
              aria-describedby={describedBy}
              autoComplete="off"
            />
          )}
        </Field>
      </ConfirmDialog>
    </div>
  )
}
