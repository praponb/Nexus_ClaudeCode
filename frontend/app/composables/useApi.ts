import { ApiError } from '~/utils/errors'
import { newCorrelationId } from '~/utils/correlation'

type HttpMethod = 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE'

export interface ApiRequestOptions {
  method?: HttpMethod
  body?: unknown
  query?: Record<string, string | number | boolean | undefined>
  headers?: Record<string, string>
  timeoutMs?: number
  /** Extra retries for idempotent GET requests on transient failures. */
  retries?: number
}

const TRANSIENT_STATUSES = new Set([502, 503, 504])
const DEFAULT_TIMEOUT_MS = 15_000
const UPLOAD_TIMEOUT_MS = 60_000

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

/**
 * Single typed wrapper around $fetch (design §8.4):
 * - one base URL from public runtime config
 * - X-Correlation-ID on every request; CSRF header on unsafe methods
 * - credentials included (session cookie auth)
 * - error envelope mapped to ApiError
 * - retries only for idempotent GET on transient failures
 */
export function useApi() {
  const config = useRuntimeConfig()
  const baseURL = String(config.public.apiBaseUrl || '').replace(/\/+$/, '')
  // Set when any non-auth request gets a 401; the app shell watches this flag.
  const sessionExpired = useState<boolean>('auth:session-expired', () => false)

  function readCookie(name: string): string | null {
    if (import.meta.server) return null
    const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`))
    return match && match[1] ? decodeURIComponent(match[1]) : null
  }

  function buildHeaders(method: HttpMethod, extra?: Record<string, string>): Record<string, string> {
    const headers: Record<string, string> = {
      'X-Correlation-ID': newCorrelationId(),
      Accept: 'application/json',
      ...extra,
    }
    if (method !== 'GET') {
      const csrf = readCookie('csrftoken')
      if (csrf) headers['X-CSRFToken'] = csrf
    }
    return headers
  }

  async function rawRequest<T>(path: string, options: ApiRequestOptions): Promise<T> {
    const method = options.method ?? 'GET'
    try {
      return await $fetch<T>(`${baseURL}${path}`, {
        method,
        body: options.body as Record<string, unknown> | undefined,
        query: options.query,
        headers: buildHeaders(method, options.headers),
        credentials: 'include',
        timeout: options.timeoutMs ?? DEFAULT_TIMEOUT_MS,
        retry: 0,
      })
    } catch (error) {
      const apiError = ApiError.fromUnknown(error)
      if (apiError.status === 401 && !path.startsWith('/auth/')) {
        sessionExpired.value = true
      }
      throw apiError
    }
  }

  async function request<T>(path: string, options: ApiRequestOptions = {}): Promise<T> {
    const method = options.method ?? 'GET'
    const retries = method === 'GET' ? (options.retries ?? 1) : 0
    let attempt = 0
    for (;;) {
      try {
        return await rawRequest<T>(path, options)
      } catch (error) {
        const apiError = error instanceof ApiError ? error : ApiError.fromUnknown(error)
        const transient = apiError.status === 0 || TRANSIENT_STATUSES.has(apiError.status)
        if (attempt < retries && transient) {
          attempt += 1
          await sleep(300 * attempt)
          continue
        }
        throw apiError
      }
    }
  }

  return {
    get: <T>(
      path: string,
      query?: ApiRequestOptions['query'],
      opts?: Omit<ApiRequestOptions, 'method' | 'query'>,
    ) => request<T>(path, { ...opts, method: 'GET', query }),
    post: <T>(path: string, body?: unknown, opts?: Omit<ApiRequestOptions, 'method' | 'body'>) =>
      request<T>(path, { ...opts, method: 'POST', body }),
    patch: <T>(path: string, body?: unknown, opts?: Omit<ApiRequestOptions, 'method' | 'body'>) =>
      request<T>(path, { ...opts, method: 'PATCH', body }),
    put: <T>(path: string, body?: unknown, opts?: Omit<ApiRequestOptions, 'method' | 'body'>) =>
      request<T>(path, { ...opts, method: 'PUT', body }),
    del: <T>(path: string, opts?: Omit<ApiRequestOptions, 'method'>) =>
      request<T>(path, { ...opts, method: 'DELETE' }),
    /** Multipart upload (60s timeout); $fetch sets the multipart boundary. */
    postForm: <T>(path: string, form: FormData, opts?: Omit<ApiRequestOptions, 'method' | 'body'>) =>
      request<T>(path, { timeoutMs: UPLOAD_TIMEOUT_MS, ...opts, method: 'POST', body: form }),
    /** Binary download through the authorized endpoint (design D-04). */
    async getBlob(path: string): Promise<Blob> {
      try {
        return await $fetch<Blob>(`${baseURL}${path}`, {
          method: 'GET',
          headers: buildHeaders('GET'),
          credentials: 'include',
          timeout: UPLOAD_TIMEOUT_MS,
          responseType: 'blob',
          retry: 0,
        })
      } catch (error) {
        throw ApiError.fromUnknown(error)
      }
    },
    async getText(path: string): Promise<string> {
      try {
        return await $fetch<string>(`${baseURL}${path}`, {
          method: 'GET',
          headers: buildHeaders('GET'),
          credentials: 'include',
          timeout: DEFAULT_TIMEOUT_MS,
          responseType: 'text',
          retry: 0,
        })
      } catch (error) {
        throw ApiError.fromUnknown(error)
      }
    },
    baseURL,
    uploadTimeout: UPLOAD_TIMEOUT_MS,
  }
}
