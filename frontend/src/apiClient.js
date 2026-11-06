// Thin fetch wrapper. Every error from the API has the shape
// { detail: string, field: string | null } and is thrown as ApiError.

export class ApiError extends Error {
  constructor(status, detail, field = null) {
    super(detail)
    this.status = status
    this.detail = detail
    this.field = field
  }
}

async function request(method, path, { body, passcode, signal } = {}) {
  const headers = {}
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  if (passcode) headers['X-Admin-Passcode'] = passcode
  let res
  try {
    res = await fetch(path, { method, headers, signal, body: body !== undefined ? JSON.stringify(body) : undefined })
  } catch (err) {
    if (err.name === 'AbortError') throw err
    throw new ApiError(0, 'Cannot reach the HireTrack server. Check that it is running.')
  }
  if (res.status === 204) return null
  const isJson = (res.headers.get('content-type') || '').includes('application/json')
  const data = isJson ? await res.json() : await res.text()
  if (!res.ok) {
    const detail = (isJson && data && data.detail) || `Request failed (${res.status})`
    throw new ApiError(res.status, typeof detail === 'string' ? detail : 'Request failed', isJson ? data.field ?? null : null)
  }
  return data
}

export const api = {
  // candidates (the table loads everything once and filters client-side; 2,000 rows is small)
  listCandidates: (params = {}) => {
    const q = new URLSearchParams({ page_size: 5000, ...params })
    return request('GET', `/api/candidates?${q}`)
  },
  getCandidate: (id) => request('GET', `/api/candidates/${id}`),
  createCandidate: (body) => request('POST', '/api/candidates', { body }),
  updateCandidate: (id, body) => request('PUT', `/api/candidates/${id}`, { body }),
  deleteCandidate: (id) => request('DELETE', `/api/candidates/${id}`),
  // jobs
  listJobs: () => request('GET', '/api/jobs'),
  getJob: (id) => request('GET', `/api/jobs/${id}`),
  createJob: (body) => request('POST', '/api/jobs', { body }),
  updateJob: (id, body) => request('PUT', `/api/jobs/${id}`, { body }),
  deleteJob: (id) => request('DELETE', `/api/jobs/${id}`),
  // matching
  runMatch: (id) => request('POST', `/api/jobs/${id}/match`),
  getResults: (id) => request('GET', `/api/jobs/${id}/results`),
  csvUrl: (id) => `/api/jobs/${id}/results.csv`,
  educationLevels: () => request('GET', '/api/education-levels'),
  stats: () => request('GET', '/api/stats'),
  demoStart: () => request('POST', '/api/demo/start'),
  // admin (passcode sent in the X-Admin-Passcode header)
  verifyPasscode: (passcode) => request('POST', '/api/admin/verify', { passcode }),
  seed: (passcode) => request('POST', '/api/admin/seed', { passcode }),
  seedLarge: (passcode) => request('POST', '/api/admin/seed-large', { passcode }),
  listBackups: (passcode) => request('GET', '/api/admin/backups', { passcode }),
  backupNow: (passcode) => request('POST', '/api/admin/backups', { passcode }),
  restoreBackup: (file, passcode) =>
    request('POST', `/api/admin/backups/${encodeURIComponent(file)}/restore`, { passcode }),
}
