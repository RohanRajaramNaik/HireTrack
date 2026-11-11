import { ChevronDown } from 'lucide-react'
import { useState } from 'react'
import { Logo } from '../components/Logo'
import { Field, Spinner } from '../components/ui'
import { ROLE_LABELS, useAuth } from '../lib/auth'

// The three accounts created on first run (see INSTALLATION_GUIDE.md).
const DEMO_ACCOUNTS = [
  { role: 'admin', email: 'admin@hiretrack.local', password: 'Admin@123' },
  { role: 'recruiter', email: 'recruiter@hiretrack.local', password: 'Recruiter@123' },
  { role: 'resource_manager', email: 'manager@hiretrack.local', password: 'Manager@123' },
]

export default function Login() {
  const { login, notice } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [errors, setErrors] = useState({})
  const [busy, setBusy] = useState(false)
  const [showDemo, setShowDemo] = useState(false)

  async function submit(e) {
    e.preventDefault()
    const errs = {}
    if (!email.trim()) errs.email = 'Enter your email address'
    if (!password) errs.password = 'Enter your password'
    setErrors(errs)
    if (Object.keys(errs).length) return
    setBusy(true)
    try {
      await login(email.trim(), password)
    } catch (err) {
      setErrors({ [err.field === 'email' ? 'email' : 'password']: err.detail })
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-4 py-12">
      <div className="w-full max-w-sm">
        <div className="mb-8 flex justify-center">
          <Logo />
        </div>
        <div className="panel px-6 py-7 sm:px-8">
          <h1 className="text-xl font-semibold tracking-tight text-ink">Sign in</h1>
          <p className="mt-1 text-base text-muted">Applicant tracking and resource allocation</p>
          {notice && (
            <p role="status" className="mt-4 rounded border border-warn/30 bg-warn-soft px-3 py-2 text-sm text-ink">
              {notice}
            </p>
          )}
          <form className="mt-6 space-y-4" onSubmit={submit} noValidate>
            <Field label="Email" error={errors.email}>
              {({ id, invalid, describedBy }) => (
                <input
                  id={id}
                  type="email"
                  autoComplete="username"
                  className="input"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  aria-invalid={invalid}
                  aria-describedby={describedBy}
                  autoFocus
                />
              )}
            </Field>
            <Field label="Password" error={errors.password}>
              {({ id, invalid, describedBy }) => (
                <input
                  id={id}
                  type="password"
                  autoComplete="current-password"
                  className="input"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  aria-invalid={invalid}
                  aria-describedby={describedBy}
                />
              )}
            </Field>
            <button type="submit" className="btn-primary w-full" disabled={busy}>
              {busy && <Spinner />}
              {busy ? 'Signing in' : 'Sign in'}
            </button>
          </form>
        </div>

        <div className="mt-4 rounded-lg border border-line bg-surface">
          <button
            type="button"
            className="flex w-full items-center justify-between px-4 py-2.5 text-sm text-muted hover:text-ink"
            onClick={() => setShowDemo((v) => !v)}
            aria-expanded={showDemo}
          >
            Demo accounts
            <ChevronDown size={15} className={`transition-transform ${showDemo ? 'rotate-180' : ''}`} aria-hidden />
          </button>
          {showDemo && (
            <ul className="border-t border-line">
              {DEMO_ACCOUNTS.map((a) => (
                <li key={a.role}>
                  <button
                    type="button"
                    className="flex w-full items-center justify-between gap-3 px-4 py-2 text-left hover:bg-subtle"
                    onClick={() => {
                      setEmail(a.email)
                      setPassword(a.password)
                      setErrors({})
                    }}
                  >
                    <span className="text-sm font-medium text-ink">{ROLE_LABELS[a.role]}</span>
                    <span className="tnum text-xs text-faint">{a.email}</span>
                  </button>
                </li>
              ))}
              <li className="border-t border-line px-4 py-2 text-xs text-faint">
                Choose one to fill in the form. Change these passwords before real use.
              </li>
            </ul>
          )}
        </div>
      </div>
    </div>
  )
}
