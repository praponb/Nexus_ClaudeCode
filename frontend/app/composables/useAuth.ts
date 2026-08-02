import type { CurrentUser } from '~/types/api'

/** Session state backed by /auth/me (design §8.3, §12). */
export function useAuth() {
  const user = useState<CurrentUser | null>('auth:user', () => null)
  const loaded = useState<boolean>('auth:loaded', () => false)
  const api = useApi()

  async function fetchUser(): Promise<CurrentUser | null> {
    try {
      user.value = await api.get<CurrentUser>('/auth/me/')
    } catch {
      user.value = null
    } finally {
      loaded.value = true
    }
    return user.value
  }

  /** Establish CSRF cookie, then log in with session-cookie auth. */
  async function login(username: string, password: string): Promise<CurrentUser> {
    await api.get('/auth/csrf/')
    const me = await api.post<CurrentUser>('/auth/login/', { username, password })
    user.value = me
    loaded.value = true
    return me
  }

  async function logout(): Promise<void> {
    try {
      await api.post('/auth/logout/')
    } catch {
      // Logout must always clear local state, even if the request fails.
    } finally {
      user.value = null
    }
  }

  function clearSession(): void {
    user.value = null
  }

  return { user, loaded, fetchUser, login, logout, clearSession }
}
