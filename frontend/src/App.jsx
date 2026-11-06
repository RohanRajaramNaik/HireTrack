import { AnimatePresence, motion } from 'framer-motion'
import { Check, Menu, Moon, Sun, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { NavLink, Route, Routes, useLocation } from 'react-router-dom'
import Admin from './pages/Admin'
import Candidates from './pages/Candidates'
import Dashboard from './pages/Dashboard'
import Jobs from './pages/Jobs'
import Results from './pages/Results'

const NAV = [
  { to: '/', label: 'Dashboard', end: true },
  { to: '/candidates', label: 'Candidates' },
  { to: '/jobs', label: 'Job Specifications' },
  { to: '/results', label: 'Results' },
  { to: '/admin', label: 'Admin' },
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

function Logo() {
  return (
    <div className="flex items-center gap-2.5">
      <svg width="22" height="22" viewBox="0 0 32 32" aria-hidden>
        <rect width="32" height="32" rx="6" fill="rgb(var(--accent))" />
        <path d="M9 8v16M9 16h9M18 8v16M22 12h4M24 12v12" stroke="rgb(var(--surface))" strokeWidth="2.6" strokeLinecap="round" />
      </svg>
      <span className="text-md font-semibold tracking-tight text-ink">HireTrack</span>
    </div>
  )
}

function TopNav() {
  const location = useLocation()
  const [menuOpen, setMenuOpen] = useState(false)
  const menuRef = useRef(null)
  const isActive = (item) =>
    item.end ? location.pathname === item.to : location.pathname === item.to || location.pathname.startsWith(item.to + '/')
  const current = NAV.find(isActive) || NAV[0]

  // Close the compact menu on navigation, outside click or Escape.
  useEffect(() => setMenuOpen(false), [location.pathname])
  useEffect(() => {
    if (!menuOpen) return undefined
    const onDown = (e) => menuRef.current && !menuRef.current.contains(e.target) && setMenuOpen(false)
    const onKey = (e) => e.key === 'Escape' && setMenuOpen(false)
    document.addEventListener('mousedown', onDown)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDown)
      document.removeEventListener('keydown', onKey)
    }
  }, [menuOpen])

  return (
    <header className="sticky top-0 z-40 border-b border-line bg-surface/95 backdrop-blur-[2px]">
      <div className="mx-auto flex h-14 max-w-content items-center gap-6 px-6 lg:gap-8">
        <NavLink to="/" className="shrink-0 rounded" aria-label="HireTrack dashboard">
          <Logo />
        </NavLink>

        {/* Full navigation: shown whenever there is room (768 px and up). Never scrolls. */}
        <nav aria-label="Main" className="hidden h-full items-stretch md:flex">
          {NAV.map((item) => {
            const active = isActive(item)
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={`relative flex items-center whitespace-nowrap px-2.5 text-base font-medium transition-colors lg:px-3 ${
                  active ? 'text-ink' : 'text-muted hover:text-ink'
                }`}
              >
                {item.label}
                {active && (
                  <motion.span
                    layoutId="nav-underline"
                    className="absolute inset-x-2.5 -bottom-px h-0.5 rounded-full bg-accent lg:inset-x-3"
                    transition={{ type: 'spring', stiffness: 500, damping: 40 }}
                  />
                )}
              </NavLink>
            )
          })}
        </nav>

        {/* Compact navigation for narrow windows: current page + dropdown menu. */}
        <div ref={menuRef} className="relative md:hidden">
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
                {NAV.map((item) => {
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
          <span className="hidden text-xs text-faint xl:inline">Local · offline</span>
          <ThemeToggle />
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
      className="mx-auto max-w-content px-6 pb-16 pt-8"
    >
      {children}
    </motion.main>
  )
}

export default function App() {
  const location = useLocation()
  const section = '/' + (location.pathname.split('/')[1] || '')
  return (
    <div className="min-h-screen">
      <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:left-2 focus:top-2 focus:z-[90] focus:rounded focus:bg-surface focus:px-3 focus:py-2">
        Skip to content
      </a>
      <TopNav />
      <div id="main">
        <AnimatePresence mode="wait" initial={false}>
          <Routes location={location} key={section}>
            <Route path="/" element={<Page><Dashboard /></Page>} />
            <Route path="/candidates" element={<Page><Candidates /></Page>} />
            <Route path="/jobs" element={<Page><Jobs /></Page>} />
            <Route path="/jobs/:jobId" element={<Page><Jobs /></Page>} />
            <Route path="/results" element={<Page><Results /></Page>} />
            <Route path="/results/:jobId" element={<Page><Results /></Page>} />
            <Route path="/admin" element={<Page><Admin /></Page>} />
            <Route path="*" element={<Page><Dashboard /></Page>} />
          </Routes>
        </AnimatePresence>
      </div>
    </div>
  )
}
