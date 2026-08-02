import { describe, expect, it } from 'vitest'
import {
  ApiError,
  isAuthError,
  isForbiddenError,
  isNotFoundError,
  isVersionConflict,
  statusToCode,
} from '~/utils/errors'

describe('ApiError.fromUnknown', () => {
  it('maps the backend error envelope (design §11.2)', () => {
    const error = ApiError.fromUnknown({
      status: 400,
      data: {
        error: {
          code: 'VALIDATION_FAILED',
          message: 'Check the highlighted fields.',
          field_errors: { name: ['This field is required.'] },
          correlation_id: '3eeab8b7-6c83-4dbe-b62b-9dbdb3cb8dab',
          retryable: false,
        },
      },
    })
    expect(error.code).toBe('VALIDATION_FAILED')
    expect(error.status).toBe(400)
    expect(error.fieldErrors.name).toEqual(['This field is required.'])
    expect(error.correlationId).toBe('3eeab8b7-6c83-4dbe-b62b-9dbdb3cb8dab')
    expect(error.retryable).toBe(false)
  })

  it('treats status-less failures as retryable network errors', () => {
    const error = ApiError.fromUnknown(new TypeError('fetch failed'))
    expect(error.code).toBe('NETWORK_ERROR')
    expect(error.status).toBe(0)
    expect(error.retryable).toBe(true)
  })

  it('falls back to status-derived codes when no envelope is present', () => {
    const error = ApiError.fromUnknown({ status: 403, message: 'Forbidden' })
    expect(error.code).toBe('PERMISSION_DENIED')
    expect(error.status).toBe(403)
  })

  it('passes ApiError instances through unchanged', () => {
    const original = new ApiError('nope', { code: 'X', status: 500 })
    expect(ApiError.fromUnknown(original)).toBe(original)
  })
})

describe('statusToCode', () => {
  it.each([
    [400, 'VALIDATION_FAILED'],
    [401, 'AUTHENTICATION_REQUIRED'],
    [403, 'PERMISSION_DENIED'],
    [404, 'NOT_FOUND'],
    [409, 'CONFLICT'],
    [429, 'RATE_LIMITED'],
    [500, 'INTERNAL_ERROR'],
  ])('maps %i to %s', (status, code) => {
    expect(statusToCode(status)).toBe(code)
  })
})

describe('error predicates', () => {
  it('detects auth, forbidden, not-found, and version conflicts', () => {
    expect(isAuthError(new ApiError('x', { status: 401 }))).toBe(true)
    expect(isForbiddenError(new ApiError('x', { status: 403 }))).toBe(true)
    expect(isNotFoundError(new ApiError('x', { status: 404 }))).toBe(true)
    expect(isVersionConflict(new ApiError('x', { status: 409, code: 'VERSION_CONFLICT' }))).toBe(true)
    expect(isVersionConflict(new ApiError('x', { status: 400 }))).toBe(false)
  })
})
