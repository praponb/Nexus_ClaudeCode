import type { CurrentUser } from '~/types/api'

export type MfaStage = 'setup' | 'verify'

export interface LoginResult {
  /** True when the password was accepted but a second factor is still owed. */
  mfaRequired: boolean
  stage: MfaStage | null
  user: CurrentUser | null
}

export interface MfaSetup {
  secret: string
  provisioning_uri: string
  qr_svg: string
  issuer: string
  account: string
}

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

  /** Server replies with either a completed session or an outstanding factor. */
  type LoginResponse = { user?: CurrentUser, mfa_required?: boolean, stage?: MfaStage }

  function adopt(session: { user?: CurrentUser }): CurrentUser | null {
    // The endpoints wrap the account as {"user": ...}; storing the envelope
    // itself would put the wrong shape in state.
    user.value = session.user ?? null
    loaded.value = true
    return user.value
  }

  /**
   * Establish CSRF cookie, then log in with session-cookie auth.
   *
   * A correct password does not always end the flow: accounts whose role
   * requires a second factor come back with `mfaRequired` and are NOT signed in
   * yet — the caller must finish via `verifyMfa` or `confirmMfa`.
   */
  async function login(username: string, password: string): Promise<LoginResult> {
    await api.get('/auth/csrf/')
    const res = await api.post<LoginResponse>('/auth/login/', { username, password })
    if (res.mfa_required) {
      return { mfaRequired: true, stage: res.stage ?? 'verify', user: null }
    }
    return { mfaRequired: false, stage: null, user: adopt(res) }
  }

  /** Enrolment payload (secret + QR) for a sign-in awaiting first-time setup. */
  async function startMfaSetup(): Promise<MfaSetup> {
    return await api.post<MfaSetup>('/auth/2fa/setup/')
  }

  /** Activate a new authenticator; completes the sign-in and returns recovery codes. */
  async function confirmMfa(code: string): Promise<{ user: CurrentUser | null, recoveryCodes: string[] }> {
    const res = await api.post<LoginResponse & { recovery_codes?: string[] }>(
      '/auth/2fa/confirm/', { code },
    )
    return { user: adopt(res), recoveryCodes: res.recovery_codes ?? [] }
  }

  /** Second factor for an enrolled account; completes the sign-in. */
  async function verifyMfa(input: { code?: string, recoveryCode?: string }): Promise<CurrentUser | null> {
    const body = input.recoveryCode ? { recovery_code: input.recoveryCode } : { code: input.code }
    return adopt(await api.post<LoginResponse>('/auth/2fa/verify/', body))
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

  return {
    user, loaded, viewUser, authResolved, fetchUser, login, logout, clearSession,
    startMfaSetup, confirmMfa, verifyMfa,
  }
}
