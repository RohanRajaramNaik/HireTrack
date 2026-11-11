import { AnimatePresence, motion } from 'framer-motion'
import { Check, ChevronDown, KeyRound, LogOut, Menu, Moon, ShieldAlert, Sun, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Link, NavLink, Route, Routes, useLocation } from 'react-router-dom'
import { api } from './apiClient'
import { Logo } from './components/Logo'
import { SlideOver } from './components/Overlay'
import { useToast } from './components/Toast'
import { EmptyState, Field, Spinner } from './components/ui'
import { ROLE_LABELS, useAuth } from './lib/auth'
import { useSkillAliases } from './lib/hooks'
import Admin from './pages/Admin'
import Candidates from './pages/Candidates'
import Dashboard from './pages/Dashboard'
import Jobs from './pages/Jobs'
import Login from './pages/Login'
import Pipeline from './pages/Pipeline'
import Resources from './pages/Resources'
import Results from './pages/Results'

// `perm` hides the item (and guards the route) for roles without access.
const NAV = [
  { to: '/', label: 'Dashboard', end: true },
  { to: '/candidates', label: 'Candidates' },
  { to: '/jobs', label: 'Jobs' },
  { to: '/results', label: 'Matching', perm: 'results:view' },
  { to: '/pipeline', label: 'Pipeline' },
  { to: '/resources', label: 'Resources' },
  { to: '/admin', label: 'Admin', perm: 'admin' },
]

function readTheme() {
  try {
    const t = localStorage.getItem('hiretrack-theme')
    if (t === 'dark' || t === 'light') return t
  } catch {
    /* storage unavailable */
  }
  return 'light'
}

function ThemeToggle() {
  const [theme, setTheme] = useState(readTheme)
  useEffect(() => {
    document.documentElement.dataset.theme = theme
    try {
      localStorage.setItem('hiretrack-theme', theme)
    } catch {
      /* ignore */
    }
  }, [theme])
  const dark = theme === 'dark'
  return (
    <button
      type="button"
      className="btn-ghost btn-sm px-2"
      onClick={() => setTheme(dark ? 'light' : 'dark')}
      aria-label={dark ? 'Switch to light theme' : 'Switch to dark theme'}
      title={dark ? 'Light theme' : 'Dark theme'}
    >
      {dark ? <Sun size={16} /> : <Moon size={16} />}
    </button>
  )
}

/** Closes a popover on outside click or Escape. */
function useDismiss(open, ref, close) {
  useEffect(() => {
    if (!open) return undefined
    const onDown = (e) => ref.current && !ref.current.contains(e.target) && close()
    const onKey = (e) => e.key === 'Escape' && close()
    document.addEventListener('mousedown', onDown)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDown)
      document.removeEventListener('keydown', onKey)
    }
  }, [open, ref, close])
}

function initials(name) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0].toUpperCase())
    .join('')
}

function AccountMenu({ onChangePassword }) {
  const { user, logout } = useAuth()
  const [open, setOpen] = useState(false)
  const ref = useRef(null)
  useDismiss(open, ref, () => setOpen(false))
  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        className="flex items-center gap-2 rounded px-1.5 py-1 hover:bg-subtle"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-haspopup="menu"
        aria-label={`Account: ${user.full_name}`}
      >
        <span className="flex h-7 w-7 items-center justify-center rounded-full bg-accent-soft text-xs font-semibold text-accent-ink">
          {initials(user.full_name)}
        </span>
        <span className="hidden text-left leading-tight xl:block">
          <span className="block text-sm font-medium text-ink">{user.full_name}</span>
          <span className="block text-2xs text-faint">{ROLE_LABELS[user.role]}</span>
        </span>
        <ChevronDown size={14} className="text-faint" aria-hidden />
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            role="menu"
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.12 }}
            className="absolute right-0 top-full z-50 mt-2 w-60 rounded-lg border border-line bg-surface p-1 shadow-pop"
          >
            <div className="px-3 py-2">
              <p className="truncate text-sm font-medium text-ink">{user.full_name}</p>
              <p className="truncate text-xs text-faint">{user.email}</p>
              <p className="mt-1 text-xs text-muted">{ROLE_LABELS[user.role]}</p>
            </div>
            <div className="my-1 border-t border-line" />
            <button
              type="button"
              role="menuitem"
              className="flex w-full items-center gap-2 rounded px-3 py-2 text-left text-base text-ink hover:bg-subtle"
              onClick={() => {
                setOpen(false)
                onChangePassword()
              }}
            >
              <KeyRound size={15} className="text-muted" aria-hidden /> Change password
            </button>
            <button
              type="button"
              role="menuitem"
              className="flex w-full items-center gap-2 rounded px-3 py-2 text-left text-base text-ink hover:bg-subtle"
              onClick={() => logout()}
            >
              <LogOut size={15} className="text-muted" aria-hidden /> Sign out
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

function ChangePassword({ open, onClose }) {
  const toast = useToast()
  const [form, setForm] = useState({ current: '', next: '', confirm: '' })
  const [errors, setErrors] = useState({})
  const [busy, setBusy] = useState(false)
  useEffect(() => {
    if (open) {
      setForm({ current: '', next: '', confirm: '' })
      setErrors({})
    }
  }, [open])
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))

  async function save(e) {
    e.preventDefault()
    const errs = {}
    if (!form.current) errs.current = 'Enter your current password'
    if (form.next.length < 8 || !/[A-Za-z]/.test(form.next) || !/[0-9]/.test(form.next))
      errs.next = 'At least 8 characters, with a letter and a number'
    if (form.confirm !== form.next) errs.confirm = 'The passwords do not match'
    setErrors(errs)
    if (Object.keys(errs).length) return
    setBusy(true)
    try {
      await api.changePassword(form.current, form.next)
      toast.success('Password changed')
      onClose()
    } catch (err) {
      setErrors({ [err.field === 'current_password' ? 'current' : 'next']: err.detail })
    } finally {
      setBusy(false)
    }
  }

  const input = (k, label, auto) => (
    <Field label={label} error={errors[k]}>
      {({ id, invalid, describedBy }) => (
        <input
          id={id}
          type="password"
          autoComplete={auto}
          className="input"
          value={form[k]}
          onChange={set(k)}
          aria-invalid={invalid}
          aria-describedby={describedBy}
        />
      )}
    </Field>
  )

  return (
    <SlideOver
      open={open}
      onClose={onClose}
      title="Change password"
      width="w-[26rem]"
      footer={
        <>
          <button type="submit" form="pw-form" className="btn-primary" disabled={busy}>
            {busy && <Spinner />} Save password
          </button>
          <button type="button" className="btn-ghost" onClick={onClose}>
            Cancel
          </button>
        </>
      }
    >
      <form id="pw-form" className="space-y-4" onSubmit={save} noValidate>
        {input('current', 'Current password', 'current-password')}
        {input('next', 'New password', 'new-password')}
        {input('confirm', 'Confirm new password', 'new-password')}
      </form>
    </SlideOver>
  )
}

function TopNav({ onChangePassword }) {
  const { can } = useAuth()
  const location = useLocation()
  const [menuOpen, setMenuOpen] = useState(false)
  const menuRef = useRef(null)
  const items = NAV.filter((i) => !i.perm || can(i.perm))
  const isActive = (item) =>
    item.end ? location.pathname === item.to : location.pathname === item.to || location.pathname.startsWith(item.to + '/')
  const current = items.find(isActive) || items[0]

  useEffect(() => setMenuOpen(false), [location.pathname])
  useDismiss(menuOpen, menuRef, () => setMenuOpen(false))

  return (
    <header className="sticky top-0 z-40 border-b border-line bg-surface/95 backdrop-blur-[2px]">
      <div className="mx-auto flex h-14 max-w-content items-center gap-6 px-4 sm:px-6 lg:gap-7">
        <NavLink to="/" className="shrink-0 rounded" aria-label="HireTrack dashboard">
          <Logo />
        </NavLink>

        {/* Full navigation from 1024 px. Never scrolls horizontally. */}
        <nav aria-label="Main" className="hidden h-full items-stretch lg:flex">
          {items.map((item) => {
            const active = isActive(item)
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={`relative flex items-center whitespace-nowrap px-2.5 text-base font-medium transition-colors xl:px-3 ${
                  active ? 'text-ink' : 'text-muted hover:text-ink'
                }`}
              >
                {item.label}
                {active && (
                  <motion.span
                    layoutId="nav-underline"
                    className="absolute inset-x-2.5 -bottom-px h-0.5 rounded-full bg-accent xl:inset-x-3"
                    transition={{ type: 'spring', stiffness: 500, damping: 40 }}
                  />
                )}
              </NavLink>
            )
          })}
        </nav>

        {/* Compact navigation for narrower windows. */}
        <div ref={menuRef} className="relative lg:hidden">
          <button
            type="button"
            className="btn-secondary btn-sm"
            onClick={() => setMenuOpen((o) => !o)}
            aria-expanded={menuOpen}
            aria-controls="mobile-nav"
          >
            {menuOpen ? <X size={15} aria-hidden /> : <Menu size={15} aria-hidden />}
            {current.label}
          </button>
          <AnimatePresence>
            {menuOpen && (
              <motion.nav
                id="mobile-nav"
                aria-label="Main"
                initial={{ opacity: 0, y: -4 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -4 }}
                transition={{ duration: 0.12 }}
                className="absolute left-0 top-full mt-2 w-56 rounded-lg border border-line bg-surface p-1 shadow-pop"
              >
                {items.map((item) => {
                  const active = isActive(item)
                  return (
                    <NavLink
                      key={item.to}
                      to={item.to}
                      end={item.end}
                      className={`flex items-center justify-between rounded px-3 py-2 text-base font-medium ${
                        active ? 'bg-accent-soft text-accent-ink' : 'text-ink hover:bg-subtle'
                      }`}
                    >
                      {item.label}
                      {active && <Check size={14} aria-hidden />}
                    </NavLink>
                  )
                })}
              </motion.nav>
            )}
          </AnimatePresence>
        </div>

        <div className="ml-auto flex shrink-0 items-center gap-1">
          <ThemeToggle />
          <AccountMenu onChangePassword={onChangePassword} />
        </div>
      </div>
    </header>
  )
}

function Page({ children }) {
  return (
    <motion.main
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, transition: { duration: 0.08 } }}
      transition={{ duration: 0.2, ease: 'easeOut' }}
      className="mx-auto max-w-content px-4 pb-16 pt-8 sm:px-6"
    >
      {children}
    </motion.main>
  )
}

/** Shows the page only to roles with `perm`; others get a clear message. */
function Guard({ perm, children }) {
  const { can, user } = useAuth()
  if (perm && !can(perm)) {
    return (
      <EmptyState
        icon={ShieldAlert}
        title="You do not have access to this page"
        action={
          <Link to="/" className="btn-secondary">
            Back to the dashboard
          </Link>
        }
      >
        Your role ({ROLE_LABELS[user.role]}) cannot open this screen. Ask an administrator if you need access.
      </EmptyState>
    )
  }
  return children
}

export default function App() {
  const { user, ready } = useAuth()
  if (!ready) return <div className="min-h-screen" aria-busy="true" />
  if (!user) return <Login />
  return <Shell />
}

function Shell() {
  useSkillAliases()
  const location = useLocation()
  const section = '/' + (location.pathname.split('/')[1] || '')
  const [pwOpen, setPwOpen] = useState(false)
  const page = (el, perm) => (
    <Page>
      <Guard perm={perm}>{el}</Guard>
    </Page>
  )
  return (
    <div className="min-h-screen">
      <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:left-2 focus:top-2 focus:z-[90] focus:rounded focus:bg-surface focus:px-3 focus:py-2">
        Skip to content
      </a>
      <TopNav onChangePassword={() => setPwOpen(true)} />
      <ChangePassword open={pwOpen} onClose={() => setPwOpen(false)} />
      <div id="main">
        <AnimatePresence mode="wait" initial={false}>
          <Routes location={location} key={section}>
            <Route path="/" element={page(<Dashboard />)} />
            <Route path="/candidates" element={page(<Candidates />)} />
            <Route path="/jobs" element={page(<Jobs />)} />
            <Route path="/jobs/:jobId" element={page(<Jobs />)} />
            <Route path="/results" element={page(<Results />, 'results:view')} />
            <Route path="/results/:jobId" element={page(<Results />, 'results:view')} />
            <Route path="/pipeline" element={page(<Pipeline />)} />
            <Route path="/pipeline/:jobId" element={page(<Pipeline />)} />
            <Route path="/resources" element={page(<Resources />)} />
            <Route path="/resources/:tab" element={page(<Resources />)} />
            <Route path="/admin" element={page(<Admin />, 'admin')} />
            <Route path="*" element={page(<Dashboard />)} />
          </Routes>
        </AnimatePresence>
      </div>
    </div>
  )
}
