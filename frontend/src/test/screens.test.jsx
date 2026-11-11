// Component tests for the key screens (Vitest + React Testing Library).
// The API module is mocked, so these test what the user sees and does,
// not the server (the server has its own pytest suite).
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('../apiClient', () => {
  class ApiError extends Error {
    constructor(status, detail, field = null) {
      super(detail)
      this.status = status
      this.detail = detail
      this.field = field
    }
  }
  const fns = [
    'login', 'me', 'changePassword', 'listUsers', 'createUser', 'updateUser', 'listCandidates', 'getCandidate',
    'createCandidate', 'updateCandidate', 'deleteCandidate', 'importCandidates', 'importTemplate', 'parseCv',
    'listJobs', 'getJob', 'createJob', 'updateJob', 'deleteJob', 'runMatch', 'getResults', 'downloadCsv',
    'educationLevels', 'skillAliases', 'stats', 'dashboard', 'demoStart', 'listApplications', 'getApplication',
    'createApplication', 'addShortlist', 'moveApplication', 'deleteApplication', 'listStaff', 'createStaff',
    'updateStaff', 'deleteStaff', 'listProjects', 'getProject', 'createProject', 'updateProject', 'deleteProject',
    'listAllocations', 'createAllocation', 'updateAllocation', 'deleteAllocation', 'verifyPassword', 'seed',
    'seedFull', 'seedLarge', 'listBackups', 'backupNow', 'restoreBackup',
  ]
  const api = Object.fromEntries(fns.map((f) => [f, vi.fn(() => Promise.resolve([]))]))
  return {
    ApiError,
    api,
    onUnauthorized: vi.fn(),
    tokenStore: { get: vi.fn(() => null), set: vi.fn() },
  }
})

/* eslint-disable import/first */
import { ApiError, api } from '../apiClient'
import App from '../App'
import { ToastProvider } from '../components/Toast'
import { AuthProvider, MockAuthProvider } from '../lib/auth'
import Admin from '../pages/Admin'
import Dashboard from '../pages/Dashboard'
import ImportPanel from '../pages/ImportPanel'
import Pipeline from '../pages/Pipeline'
import Resources from '../pages/Resources'

const FUTURE = { v7_startTransition: true, v7_relativeSplatPath: true }

const USERS = {
  admin: { user_id: 1, full_name: 'System Administrator', email: 'admin@hiretrack.local', role: 'admin', is_active: true },
  recruiter: { user_id: 2, full_name: 'Nomvula Khumalo', email: 'recruiter@hiretrack.local', role: 'recruiter', is_active: true },
  resource_manager: { user_id: 3, full_name: 'Pieter Botha', email: 'manager@hiretrack.local', role: 'resource_manager', is_active: true },
}

function renderAs(role, ui, path = '/', routePath = '*') {
  return render(
    <MemoryRouter initialEntries={[path]} future={FUTURE}>
      <ToastProvider>
        <MockAuthProvider user={USERS[role]}>
          <Routes>
            <Route path={routePath} element={ui} />
          </Routes>
        </MockAuthProvider>
      </ToastProvider>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  Object.values(api).forEach((fn) => fn.mockImplementation(() => Promise.resolve([])))
  api.dashboard.mockResolvedValue(DASHBOARD)
})

/* ------------------------------------------------------------------ login */
describe('Login screen', () => {
  const renderLogin = () =>
    render(
      <MemoryRouter future={FUTURE}>
        <ToastProvider>
          <AuthProvider>
            <App />
          </AuthProvider>
        </ToastProvider>
      </MemoryRouter>,
    )

  it('asks for both fields before calling the server', async () => {
    renderLogin()
    await userEvent.click(await screen.findByRole('button', { name: 'Sign in' }))
    expect(screen.getByText('Enter your email address')).toBeInTheDocument()
    expect(screen.getByText('Enter your password')).toBeInTheDocument()
    expect(api.login).not.toHaveBeenCalled()
  })

  it('shows the server message on a wrong password', async () => {
    api.login.mockRejectedValue(new ApiError(401, 'Incorrect email or password', 'password'))
    renderLogin()
    await userEvent.type(await screen.findByLabelText('Email'), 'admin@hiretrack.local')
    await userEvent.type(screen.getByLabelText('Password'), 'wrong')
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }))
    expect(await screen.findByText('Incorrect email or password')).toBeInTheDocument()
  })

  it('fills a demo account and signs in to the dashboard', async () => {
    api.login.mockResolvedValue({ access_token: 't', user: USERS.recruiter })
    renderLogin()
    await userEvent.click(await screen.findByRole('button', { name: 'Demo accounts' }))
    await userEvent.click(screen.getByRole('button', { name: /Recruiter \(HR\)/ }))
    expect(screen.getByLabelText('Email')).toHaveValue('recruiter@hiretrack.local')
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }))
    expect(api.login).toHaveBeenCalledWith('recruiter@hiretrack.local', 'Recruiter@123')
    expect(await screen.findByRole('heading', { name: 'Dashboard' })).toBeInTheDocument()
  })
})

/* ---------------------------------------------------------- role-based UI */
describe('Navigation by role', () => {
  const navLabels = () =>
    within(screen.getAllByRole('navigation', { name: 'Main' })[0])
      .getAllByRole('link')
      .map((a) => a.textContent)

  it('recruiters see Matching but not Admin', async () => {
    renderAs('recruiter', <App />)
    await screen.findByRole('heading', { name: 'Dashboard' })
    expect(navLabels()).toEqual(['Dashboard', 'Candidates', 'Jobs', 'Matching', 'Pipeline', 'Resources'])
  })

  it('resource managers see neither Matching nor Admin', async () => {
    renderAs('resource_manager', <App />)
    await screen.findByRole('heading', { name: 'Dashboard' })
    expect(navLabels()).toEqual(['Dashboard', 'Candidates', 'Jobs', 'Pipeline', 'Resources'])
  })

  it('administrators see every section', async () => {
    renderAs('admin', <App />)
    await screen.findByRole('heading', { name: 'Dashboard' })
    expect(navLabels()).toContain('Admin')
  })

  it('a direct link to a forbidden page shows a clear message', async () => {
    renderAs('recruiter', <App />, '/admin')
    expect(await screen.findByText('You do not have access to this page')).toBeInTheDocument()
    expect(api.listUsers).not.toHaveBeenCalled()
  })
})

/* -------------------------------------------------------------- dashboard */
const DASHBOARD = {
  counts: {
    candidates: 600, jobs_open: 30, jobs_total: 33, applications_active: 626, hires_30_days: 14,
    staff_active: 75, staff_bench: 9, average_utilisation: 58.2,
  },
  funnel: [
    { stage: 'applied', label: 'Applied', current: 280, reached: 882, conversion: null },
    { stage: 'screened', label: 'Screened', current: 190, reached: 494, conversion: 56 },
    { stage: 'interview', label: 'Interview', current: 95, reached: 232, conversion: 47 },
    { stage: 'offer', label: 'Offer', current: 54, reached: 99, conversion: 42.7 },
    { stage: 'hired', label: 'Hired', current: 32, reached: 32, conversion: 32.3 },
    { stage: 'rejected', label: 'Rejected', current: 224, reached: null, conversion: null },
  ],
  applications_per_job: [{ job_id: 7, job_title: 'Database Administrator', count: 32 }],
  hires_per_month: [
    { month: '2026-10', label: 'Oct', count: 12 },
    { month: '2026-11', label: 'Nov', count: 5 },
  ],
  utilisation_bands: { bench: 9, light: 10, healthy: 40, full: 16 },
  recent_activity: [
    { event_id: 1, application_id: 1, candidate_name: 'Ayanda Zulu', job_title: 'Cloud Engineer', from_stage: 'interview', to_stage: 'offer', to_label: 'Offer', changed_by: 'Nomvula Khumalo', changed_at: new Date().toISOString() },
  ],
  matching: { last_run_at: null, last_run_job_title: null, last_run_job_id: null, average_score: null, embedder: 'all-MiniLM-L6-v2' },
}

describe('Dashboard', () => {
  it('shows the key counts and every chart', async () => {
    renderAs('admin', <Dashboard />)
    expect(await screen.findByText('600')).toBeInTheDocument()
    expect(screen.getByText('626')).toBeInTheDocument()
    expect(screen.getByText('58%')).toBeInTheDocument()
    expect(screen.getByText('14 hired in the last 30 days')).toBeInTheDocument()
    // funnel and utilisation charts also expose their numbers as tables
    expect(screen.getByRole('table', { name: /reached each pipeline stage/ })).toBeInTheDocument()
    expect(screen.getByRole('table', { name: /utilisation band/ })).toBeInTheDocument()
    expect(screen.getByRole('table', { name: /Hires per month/ })).toBeInTheDocument()
    expect(screen.getByText('224 rejected or withdrawn')).toBeInTheDocument()
    expect(screen.getByText('Ayanda Zulu')).toBeInTheDocument()
  })

  it('clickable chart bars are real buttons with names (keyboard and screen readers)', async () => {
    renderAs('admin', <Dashboard />)
    const bench = await screen.findByRole('button', { name: 'Bench (0%): 9' })
    act(() => bench.focus())
    expect(bench).toHaveFocus()
    expect(screen.getByRole('button', { name: 'Database Administrator: 32' })).toBeInTheDocument()
  })

  it('hides hiring actions from resource managers', async () => {
    renderAs('resource_manager', <Dashboard />)
    await screen.findByText('600')
    expect(screen.queryByRole('button', { name: /Guided matching demo/ })).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Manage projects/ })).toBeInTheDocument()
  })
})

/* --------------------------------------------------------------- pipeline */
const APPS = [
  { application_id: 1, candidate_id: 10, candidate_name: 'Ayanda Zulu', candidate_titles: 'Developer', candidate_location: 'Durban', years_experience: 4, job_id: 5, job_title: 'Backend Developer', stage: 'applied', match_score: 81.2, applied_at: '2026-11-01T09:00:00', updated_at: '2026-11-01T09:00:00', allowed_moves: ['screened', 'rejected'] },
  { application_id: 2, candidate_id: 11, candidate_name: 'Lerato Moloi', candidate_titles: 'Developer', candidate_location: null, years_experience: 2, job_id: 5, job_title: 'Backend Developer', stage: 'interview', match_score: null, applied_at: '2026-10-20T09:00:00', updated_at: '2026-11-02T09:00:00', allowed_moves: ['offer', 'rejected'] },
]
const DETAIL = {
  ...APPS[0],
  events: [{ event_id: 1, from_stage: null, to_stage: 'applied', changed_by_name: 'Nomvula Khumalo', changed_at: '2026-11-01T09:00:00', note: 'Referred' }],
}

describe('Pipeline board', () => {
  beforeEach(() => {
    api.listJobs.mockResolvedValue([{ job_id: 5, job_title: 'Backend Developer', status: 'open', location: 'Cape Town' }])
    api.listApplications.mockResolvedValue(APPS)
    api.getApplication.mockResolvedValue(DETAIL)
  })

  it('groups applications into stage columns with counts', async () => {
    renderAs('recruiter', <Pipeline />, '/pipeline/5', '/pipeline/:jobId')
    const applied = await screen.findByRole('region', { name: 'Applied: 1' })
    expect(within(applied).getByText('Ayanda Zulu')).toBeInTheDocument()
    expect(screen.getByRole('region', { name: 'Interview: 1' })).toBeInTheDocument()
    expect(screen.getByRole('region', { name: 'Hired: 0' })).toBeInTheDocument()
    expect(api.listApplications).toHaveBeenCalledWith({ job_id: 5 })
  })

  it('opens the history and moves to the next stage with a note', async () => {
    api.moveApplication.mockResolvedValue({
      ...DETAIL,
      stage: 'screened',
      allowed_moves: ['interview', 'rejected'],
      events: [...DETAIL.events, { event_id: 2, from_stage: 'applied', to_stage: 'screened', changed_by_name: 'Nomvula Khumalo', changed_at: '2026-11-03T09:00:00', note: 'Good CV' }],
    })
    renderAs('recruiter', <Pipeline />, '/pipeline/5', '/pipeline/:jobId')
    await userEvent.click(await screen.findByText('Ayanda Zulu'))
    expect(await screen.findByText('Referred')).toBeInTheDocument()
    await userEvent.type(screen.getByLabelText(/Note for the next change/), 'Good CV')
    await userEvent.click(screen.getByRole('button', { name: 'Mark as screened' }))
    expect(api.moveApplication).toHaveBeenCalledWith(1, 'screened', 'Good CV')
    expect(await screen.findByRole('button', { name: 'Move to interview' })).toBeInTheDocument()
  })

  it('shows the server reason when a move is refused', async () => {
    api.moveApplication.mockRejectedValue(new ApiError(422, 'This job is closed, so nobody else can be hired for it', 'stage'))
    renderAs('recruiter', <Pipeline />, '/pipeline/5', '/pipeline/:jobId')
    await userEvent.click(await screen.findByText('Ayanda Zulu'))
    await userEvent.click(await screen.findByRole('button', { name: 'Mark as screened' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('nobody else can be hired')
  })

  it('is read-only for resource managers', async () => {
    renderAs('resource_manager', <Pipeline />, '/pipeline/5', '/pipeline/:jobId')
    await userEvent.click(await screen.findByText('Ayanda Zulu'))
    await screen.findByText('Referred')
    expect(screen.queryByRole('button', { name: 'Mark as screened' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Add candidate/ })).not.toBeInTheDocument()
  })
})

/* -------------------------------------------------------------- resources */
const STAFF = [
  { staff_id: 1, full_name: 'Johan Venter', email: null, role_title: 'Software Developer', location: 'Pretoria', source: 'existing', candidate_id: null, is_active: true, utilisation: 70, band: 'healthy', current_projects: ['Claims Portal'] },
  { staff_id: 2, full_name: 'Liezl Steyn', email: null, role_title: 'QA Engineer', location: 'Durban', source: 'hired', candidate_id: 4, is_active: true, utilisation: 0, band: 'bench', current_projects: [] },
]
const PROJECTS = [
  { project_id: 9, name: 'Claims Portal', client: 'Fynbos Insurance', description: null, start_date: '2026-10-01', end_date: '2027-03-31', status: 'active', team_size: 1, allocated_percent: 70 },
]

describe('Resource allocation', () => {
  beforeEach(() => {
    api.listStaff.mockResolvedValue(STAFF)
    api.listProjects.mockResolvedValue(PROJECTS)
    api.listAllocations.mockResolvedValue([])
  })

  it('lists staff with utilisation and filters by band', async () => {
    renderAs('resource_manager', <Resources />, '/resources', '/resources')
    expect(await screen.findByText('Johan Venter')).toBeInTheDocument()
    expect(screen.getByText('70%')).toBeInTheDocument()
    expect(screen.getByText(/2 active · average 35% booked today · 1 on the bench/)).toBeInTheDocument()
    await userEvent.selectOptions(screen.getByLabelText('Utilisation'), 'bench')
    expect(screen.queryByText('Johan Venter')).not.toBeInTheDocument()
    expect(screen.getByText('Liezl Steyn')).toBeInTheDocument()
  })

  it('checks allocation dates before sending and shows the over-allocation reason', async () => {
    api.createAllocation.mockRejectedValue(
      new ApiError(422, 'This would book the person at 120% on 11 Nov 2026 (already 70% allocated). The most you can add for these dates is 30%.', 'allocation_percent'),
    )
    renderAs('resource_manager', <Resources />, '/resources', '/resources')
    await userEvent.click(await screen.findByText('Liezl Steyn'))
    const form = await screen.findByTestId('allocation-form')
    await userEvent.selectOptions(within(form).getByLabelText('Project'), '9')
    fireEvent.change(within(form).getByLabelText('End'), { target: { value: '2026-01-01' } })
    await userEvent.click(within(form).getByRole('button', { name: /Save allocation/ }))
    expect(within(form).getByText('End date cannot be before the start date')).toBeInTheDocument()
    expect(api.createAllocation).not.toHaveBeenCalled()

    fireEvent.change(within(form).getByLabelText('End'), { target: { value: '2027-03-31' } })
    await userEvent.click(within(form).getByRole('button', { name: /Save allocation/ }))
    expect(await within(form).findByText(/most you can add for these dates is 30%/)).toBeInTheDocument()
  })

  it('recruiters can view but not change staff', async () => {
    renderAs('recruiter', <Resources />, '/resources', '/resources')
    await screen.findByText('Johan Venter')
    expect(screen.queryByRole('button', { name: /Add staff member/ })).not.toBeInTheDocument()
  })
})

/* ----------------------------------------------------------------- import */
describe('Candidate import', () => {
  it('reports imported, skipped and failed rows', async () => {
    api.importCandidates.mockResolvedValue({
      created: 2,
      skipped: 1,
      errors: [{ row: 4, field: 'years_experience', message: 'Cannot be less than 0' }],
    })
    const onImported = vi.fn()
    renderAs('recruiter', <ImportPanel open onClose={() => {}} onImported={onImported} />)
    const file = new File(['full_name\n'], 'people.csv', { type: 'text/csv' })
    await userEvent.upload(screen.getByLabelText('File'), file)
    expect(screen.getByText('people.csv')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Import file' }))
    expect(await screen.findByText('Rows with errors')).toBeInTheDocument()
    const table = screen.getByRole('table')
    expect(within(table).getByText('Years')).toBeInTheDocument()
    expect(within(table).getByText('Cannot be less than 0')).toBeInTheDocument()
    expect(onImported).toHaveBeenCalled()
  })

  it('shows a file-level error such as missing columns', async () => {
    api.importCandidates.mockRejectedValue(new ApiError(422, 'Missing column(s): skills', 'file'))
    renderAs('recruiter', <ImportPanel open onClose={() => {}} />)
    await userEvent.upload(screen.getByLabelText('File'), new File(['x'], 'bad.csv'))
    await userEvent.click(screen.getByRole('button', { name: 'Import file' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Missing column(s): skills')
  })
})

/* ------------------------------------------------------------------ admin */
describe('Administration', () => {
  beforeEach(() => {
    api.listUsers.mockResolvedValue(Object.values(USERS).map((u) => ({ ...u, created_at: '2026-11-01T00:00:00', last_login_at: null })))
    api.listBackups.mockResolvedValue([])
  })

  it('lists users with their roles', async () => {
    renderAs('admin', <Admin />)
    expect(await screen.findByText('Pieter Botha')).toBeInTheDocument()
    expect(screen.getByText('Resource Manager')).toBeInTheDocument()
    expect(screen.getByText('You')).toBeInTheDocument()
  })

  it('validates a new user before saving', async () => {
    renderAs('admin', <Admin />)
    await userEvent.click(await screen.findByRole('button', { name: /Add user/ }))
    await userEvent.type(screen.getByLabelText('Full name'), 'Lerato Moloi')
    await userEvent.type(screen.getByLabelText('Email'), 'lerato@hiretrack.local')
    await userEvent.type(screen.getByLabelText('Password'), 'short')
    await userEvent.click(screen.getByRole('button', { name: 'Create user' }))
    expect(screen.getByText('At least 8 characters, with a letter and a number')).toBeInTheDocument()
    expect(api.createUser).not.toHaveBeenCalled()
  })

  it('needs the admin password before replacing data', async () => {
    api.seedFull.mockRejectedValue(new ApiError(401, 'Incorrect password', 'password'))
    renderAs('admin', <Admin />)
    await userEvent.click(await screen.findByRole('button', { name: 'Load full dataset' }))
    const dialog = await screen.findByRole('alertdialog')
    await userEvent.click(within(dialog).getByRole('button', { name: 'Replace data' }))
    expect(within(dialog).getByText('Enter your password to confirm')).toBeInTheDocument()
    expect(api.seedFull).not.toHaveBeenCalled()
    await userEvent.type(within(dialog).getByLabelText('Your password'), 'nope')
    await userEvent.click(within(dialog).getByRole('button', { name: 'Replace data' }))
    await waitFor(() => expect(api.seedFull).toHaveBeenCalledWith('nope'))
    expect(await within(dialog).findByText('Incorrect password')).toBeInTheDocument()
  })
})
