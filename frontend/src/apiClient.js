// Thin fetch wrapper. Every error from the API has the shape
// { detail: string, field: string | null } and is thrown as ApiError.
//
// The sign-in token is kept in sessionStorage (cleared when the browser tab
// closes) and sent as "Authorization: Bearer <token>" on every request.
// A 401 from any call except the login itself signs the user out.

const TOKEN_KEY = 'hiretrack-token'

export class ApiError extends Error {
  constructor(status, detail, field = null) {
    super(detail)
    this.status = status
    this.detail = detail
    this.field = field
  }
}

let unauthorizedHandler = null
/** App registers a callback that clears the session and shows the sign-in screen. */
export function onUnauthorized(fn) {
  unauthorizedHandler = fn
}

export const tokenStore = {
  get() {
    try {
      return sessionStorage.getItem(TOKEN_KEY)
    } catch {
      return null
    }
  },
  set(token) {
    try {
      if (token) sessionStorage.setItem(TOKEN_KEY, token)
      else sessionStorage.removeItem(TOKEN_KEY)
    } catch {
      /* storage unavailable: the session lasts until reload */
    }
  },
}

async function send(method, path, { body, form, confirmPassword, signal } = {}) {
  const headers = {}
  const token = tokenStore.get()
  if (token) headers.Authorization = `Bearer ${token}`
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  if (confirmPassword) headers['X-Confirm-Password'] = confirmPassword
  try {
    return await fetch(path, {
      method,
      headers,
      signal,
      body: form || (body !== undefined ? JSON.stringify(body) : undefined),
    })
  } catch (err) {
    if (err.name === 'AbortError') throw err
    throw new ApiError(0, 'Cannot reach the HireTrack server. Check that it is running.')
  }
}

async function fail(res, path) {
  const isJson = (res.headers.get('content-type') || '').includes('application/json')
  const data = isJson ? await res.json() : null
  if (res.status === 401 && !path.startsWith('/api/auth/login') && data?.field !== 'password' && data?.field !== 'current_password') {
    unauthorizedHandler?.(data?.detail)
  }
  const detail = (data && data.detail) || `Request failed (${res.status})`
  return new ApiError(res.status, typeof detail === 'string' ? detail : 'Request failed', data ? data.field ?? null : null)
}

async function request(method, path, opts = {}) {
  const res = await send(method, path, opts)
  if (!res.ok) throw await fail(res, path)
  if (res.status === 204) return null
  const isJson = (res.headers.get('content-type') || '').includes('application/json')
  return isJson ? res.json() : res.text()
}

function upload(path, file) {
  const form = new FormData()
  form.append('file', file)
  return request('POST', path, { form })
}

/** Download a file from an authenticated endpoint and save it with its server name. */
async function download(path, fallbackName) {
  const res = await send('GET', path)
  if (!res.ok) throw await fail(res, path)
  const blob = await res.blob()
  const cd = res.headers.get('content-disposition') || ''
  const name = (cd.match(/filename="?([^"]+)"?/) || [])[1] || fallbackName
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = name
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
  return name
}

const qs = (params) => {
  const q = new URLSearchParams()
  Object.entries(params || {}).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') q.set(k, v)
  })
  const s = q.toString()
  return s ? `?${s}` : ''
}

export const api = {
  // auth and users
  login: (email, password) => request('POST', '/api/auth/login', { body: { email, password } }),
  me: () => request('GET', '/api/auth/me'),
  changePassword: (current_password, new_password) =>
    request('POST', '/api/auth/change-password', { body: { current_password, new_password } }),
  listUsers: () => request('GET', '/api/users'),
  createUser: (body) => request('POST', '/api/users', { body }),
  updateUser: (id, body) => request('PUT', `/api/users/${id}`, { body }),
  // candidates (the table loads everything once and filters client-side; 2,000 rows is small)
  listCandidates: (params = {}) => request('GET', `/api/candidates${qs({ page_size: 5000, ...params })}`),
  getCandidate: (id) => request('GET', `/api/candidates/${id}`),
  createCandidate: (body) => request('POST', '/api/candidates', { body }),
  updateCandidate: (id, body) => request('PUT', `/api/candidates/${id}`, { body }),
  deleteCandidate: (id) => request('DELETE', `/api/candidates/${id}`),
  importCandidates: (file) => upload('/api/candidates/import', file),
  importTemplate: () => download('/api/candidates/import/template', 'hiretrack-candidate-import-template.csv'),
  parseCv: (file) => upload('/api/candidates/parse-cv', file),
  // jobs
  listJobs: () => request('GET', '/api/jobs'),
  getJob: (id) => request('GET', `/api/jobs/${id}`),
  createJob: (body) => request('POST', '/api/jobs', { body }),
  updateJob: (id, body) => request('PUT', `/api/jobs/${id}`, { body }),
  deleteJob: (id) => request('DELETE', `/api/jobs/${id}`),
  // matching
  runMatch: (id) => request('POST', `/api/jobs/${id}/match`),
  getResults: (id) => request('GET', `/api/jobs/${id}/results`),
  downloadCsv: (id) => download(`/api/jobs/${id}/results.csv`, 'hiretrack-results.csv'),
  educationLevels: () => request('GET', '/api/education-levels'),
  skillAliases: () => request('GET', '/api/skill-aliases'),
  stats: () => request('GET', '/api/stats'),
  dashboard: () => request('GET', '/api/dashboard'),
  demoStart: () => request('POST', '/api/demo/start'),
  // pipeline
  listApplications: (params) => request('GET', `/api/applications${qs(params)}`),
  getApplication: (id) => request('GET', `/api/applications/${id}`),
  createApplication: (body) => request('POST', '/api/applications', { body }),
  addShortlist: (job_id, candidate_ids) => request('POST', '/api/applications/bulk', { body: { job_id, candidate_ids } }),
  moveApplication: (id, stage, note) => request('POST', `/api/applications/${id}/stage`, { body: { stage, note } }),
  deleteApplication: (id) => request('DELETE', `/api/applications/${id}`),
  // resources
  listStaff: (params) => request('GET', `/api/staff${qs(params)}`),
  createStaff: (body) => request('POST', '/api/staff', { body }),
  updateStaff: (id, body) => request('PUT', `/api/staff/${id}`, { body }),
  deleteStaff: (id) => request('DELETE', `/api/staff/${id}`),
  listProjects: (params) => request('GET', `/api/projects${qs(params)}`),
  getProject: (id) => request('GET', `/api/projects/${id}`),
  createProject: (body) => request('POST', '/api/projects', { body }),
  updateProject: (id, body) => request('PUT', `/api/projects/${id}`, { body }),
  deleteProject: (id) => request('DELETE', `/api/projects/${id}`),
  listAllocations: (params) => request('GET', `/api/allocations${qs(params)}`),
  createAllocation: (body) => request('POST', '/api/allocations', { body }),
  updateAllocation: (id, body) => request('PUT', `/api/allocations/${id}`, { body }),
  deleteAllocation: (id) => request('DELETE', `/api/allocations/${id}`),
  // admin (destructive actions re-send the admin's password)
  verifyPassword: (pw) => request('POST', '/api/admin/verify', { confirmPassword: pw }),
  seed: (pw) => request('POST', '/api/admin/seed', { confirmPassword: pw }),
  seedFull: (pw) => request('POST', '/api/admin/seed-full', { confirmPassword: pw }),
  seedLarge: (pw) => request('POST', '/api/admin/seed-large', { confirmPassword: pw }),
  listBackups: () => request('GET', '/api/admin/backups'),
  backupNow: () => request('POST', '/api/admin/backups'),
  restoreBackup: (file, pw) =>
    request('POST', `/api/admin/backups/${encodeURIComponent(file)}/restore`, { confirmPassword: pw }),
}
