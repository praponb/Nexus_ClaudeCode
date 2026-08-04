import type { CurrentUser } from '~/types/api'

/** Session state backed by /auth/me (design §8.3, §12). */
export function useAuth() {
  const user = useState<CurrentUser | null>('auth:user', () => null)
  const loaded = useState<boolean>('auth:loaded', () => false)
  const hydrated = useState<boolean>('app:hydrated', () => false)
  const api = useApi()

  /**
   * Hydration-safe view of the session, for rendering only.
   *
   * `user`/`loaded` are resolved by `auth.global.ts` before the client
   * hydrates, but the SSR shell rendered with no session at all. Templates
   * must read these instead, so the first client render reproduces the
   * server markup and Vue never has to patch a mismatch (see
   * `plugins/hydrated.client.ts`). Keep using `user`/`loaded` for logic,
   * middleware, and anything that never reaches the DOM.
   */
  const viewUser = computed<CurrentUser | null>(() => (hydrated.value ? user.value : null))
  const authResolved = computed<boolean>(() => hydrated.value && loaded.value)

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

  return { user, loaded, viewUser, authResolved, fetchUser, login, logout, clearSession }
}
