import { AnimatePresence, motion } from 'framer-motion'
import { Moon, Sun } from 'lucide-react'
import { useEffect, useState } from 'react'
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
  const isActive = (item) =>
    item.end ? location.pathname === item.to : location.pathname === item.to || location.pathname.startsWith(item.to + '/')
  return (
    <header className="sticky top-0 z-40 border-b border-line bg-surface/95 backdrop-blur-[2px]">
      <div className="mx-auto flex h-14 max-w-content items-center gap-8 px-6">
        <NavLink to="/" className="rounded" aria-label="HireTrack dashboard">
          <Logo />
        </NavLink>
        <nav aria-label="Main" className="flex h-full items-stretch gap-1 overflow-x-auto">
          {NAV.map((item) => {
            const active = isActive(item)
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={`relative flex items-center whitespace-nowrap px-3 text-base font-medium transition-colors ${
                  active ? 'text-ink' : 'text-muted hover:text-ink'
                }`}
              >
                {item.label}
                {active && (
                  <motion.span
                    layoutId="nav-underline"
                    className="absolute inset-x-3 -bottom-px h-0.5 rounded-full bg-accent"
                    transition={{ type: 'spring', stiffness: 500, damping: 40 }}
                  />
                )}
              </NavLink>
            )
          })}
        </nav>
        <div className="ml-auto flex items-center gap-1">
          <span className="hidden text-xs text-faint lg:inline">Local · offline</span>
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
