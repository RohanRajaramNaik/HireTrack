import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { api, onUnauthorized, tokenStore } from '../apiClient'

/** What each role may do. The server enforces the same rules; this only hides
 * buttons and menu items a user cannot use. */
export const PERMISSIONS = {
  'hiring:write': ['admin', 'recruiter'], // candidates, jobs, matching, pipeline moves
  'resources:write': ['admin', 'resource_manager'], // staff, projects, allocations
  'results:view': ['admin', 'recruiter'],
  admin: ['admin'],
}

export const ROLE_LABELS = {
  admin: 'Administrator',
  recruiter: 'Recruiter (HR)',
  resource_manager: 'Resource Manager',
}

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [ready, setReady] = useState(false)
  const [notice, setNotice] = useState(null)

  const logout = useCallback((message = null) => {
    tokenStore.set(null)
    setUser(null)
    setNotice(message)
  }, [])

  // Restore the session after a page reload.
  useEffect(() => {
    onUnauthorized((detail) => logout(detail || 'Please sign in again.'))
    if (!tokenStore.get()) {
      setReady(true)
      return
    }
    api
      .me()
      .then(setUser)
      .catch(() => tokenStore.set(null))
      .finally(() => setReady(true))
  }, [logout])

  const login = useCallback(async (email, password) => {
    const res = await api.login(email, password)
    tokenStore.set(res.access_token)
    setNotice(null)
    setUser(res.user)
    return res.user
  }, [])

  const value = useMemo(
    () => ({
      user,
      ready,
      notice,
      login,
      logout,
      setUser,
      can: (permission) => Boolean(user && (PERMISSIONS[permission] || []).includes(user.role)),
    }),
    [user, ready, notice, login, logout],
  )
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}

/** For tests and isolated component rendering. */
export function MockAuthProvider({ user, children }) {
  const value = useMemo(
    () => ({
      user,
      ready: true,
      notice: null,
      login: async () => user,
      logout: () => {},
      setUser: () => {},
      can: (permission) => Boolean(user && (PERMISSIONS[permission] || []).includes(user.role)),
    }),
    [user],
  )
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
