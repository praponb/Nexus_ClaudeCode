import type { ApiErrorBody } from '~/types/api'

export interface ApiErrorInit {
  code?: string
  status?: number
  fieldErrors?: Record<string, string[]>
  correlationId?: string | null
  retryable?: boolean
}

/** Normalized API error mapped from the backend error envelope (design §11.2). */
export class ApiError extends Error {
  readonly code: string
  readonly status: number
  readonly fieldErrors: Record<string, string[]>
  readonly correlationId: string | null
  readonly retryable: boolean

  constructor(message: string, init: ApiErrorInit = {}) {
    super(message)
    this.name = 'ApiError'
    this.code = init.code ?? 'REQUEST_FAILED'
    this.status = init.status ?? 0
    this.fieldErrors = init.fieldErrors ?? {}
    this.correlationId = init.correlationId ?? null
    this.retryable = init.retryable ?? false
  }

  static fromUnknown(error: unknown): ApiError {
    if (error instanceof ApiError) return error

    const e = error as {
      status?: number
      statusCode?: number
      data?: unknown
      message?: string
    } | null
    const status = e?.status ?? e?.statusCode ?? 0
    const body = e?.data

    if (body && typeof body === 'object' && 'error' in body) {
      const env = (body as ApiErrorBody).error
      return new ApiError(env.message || 'The request could not be completed.', {
        code: env.code || statusToCode(status),
        status,
        fieldErrors: env.field_errors ?? {},
        correlationId: env.correlation_id ?? null,
        retryable: env.retryable ?? false,
      })
    }

    if (!status) {
      return new ApiError('Network error — check your connection, then try again.', {
        code: 'NETWORK_ERROR',
        status: 0,
        retryable: true,
      })
    }

    return new ApiError(e?.message || 'The request could not be completed.', {
      code: statusToCode(status),
      status,
    })
  }
}

export function statusToCode(status: number): string {
  if (status === 400) return 'VALIDATION_FAILED'
  if (status === 401) return 'AUTHENTICATION_REQUIRED'
  if (status === 403) return 'PERMISSION_DENIED'
  if (status === 404) return 'NOT_FOUND'
  if (status === 409) return 'CONFLICT'
  if (status === 429) return 'RATE_LIMITED'
  if (status >= 500) return 'INTERNAL_ERROR'
  return 'REQUEST_FAILED'
}

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError
}

export function isAuthError(error: unknown): boolean {
  return error instanceof ApiError && error.status === 401
}

export function isForbiddenError(error: unknown): boolean {
  return error instanceof ApiError && error.status === 403
}

export function isNotFoundError(error: unknown): boolean {
  return error instanceof ApiError && error.status === 404
}

export function isVersionConflict(error: unknown): boolean {
  return (
    error instanceof ApiError &&
    (error.code === 'VERSION_CONFLICT' || error.status === 409)
  )
}
