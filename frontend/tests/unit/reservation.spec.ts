import { describe, expect, it } from 'vitest'
import { toIsoDateTime, toLocalInputValue, validateReservationWindow } from '~/utils/reservation'

describe('toLocalInputValue', () => {
  it('formats a date for datetime-local inputs (zero-padded, no timezone)', () => {
    const date = new Date(2026, 0, 5, 9, 7, 33) // 2026-01-05 09:07 local
    expect(toLocalInputValue(date)).toBe('2026-01-05T09:07')
  })
})

describe('toIsoDateTime', () => {
  it('converts a datetime-local value to an ISO string with timezone', () => {
    const iso = toIsoDateTime('2026-01-05T09:07')
    expect(iso).toMatch(/^2026-01-05T\d{2}:\d{2}:00\.000Z$/)
    expect(new Date(iso).getTime()).toBe(new Date('2026-01-05T09:07').getTime())
  })
})

describe('validateReservationWindow', () => {
  const now = new Date('2026-01-05T12:00:00')

  it('requires both start and end', () => {
    expect(validateReservationWindow('', '2026-01-06T10:00', now)).toMatch(/starts/)
    expect(validateReservationWindow('2026-01-06T09:00', '', now)).toMatch(/ends/)
  })

  it('rejects invalid date values', () => {
    expect(validateReservationWindow('not-a-date', '2026-01-06T10:00', now)).toMatch(/valid/)
  })

  it('rejects end times at or before the start', () => {
    expect(validateReservationWindow('2026-01-06T10:00', '2026-01-06T10:00', now)).toMatch(/after the start/)
    expect(validateReservationWindow('2026-01-06T10:00', '2026-01-06T09:00', now)).toMatch(/after the start/)
  })

  it('rejects windows entirely in the past', () => {
    expect(validateReservationWindow('2026-01-04T09:00', '2026-01-04T10:00', now)).toMatch(/future/)
  })

  it('accepts a valid future window (including one already in progress)', () => {
    expect(validateReservationWindow('2026-01-06T09:00', '2026-01-06T10:00', now)).toBeNull()
    // In-progress window: started earlier, ends later — still reservable UX-wise.
    expect(validateReservationWindow('2026-01-05T10:00', '2026-01-05T14:00', now)).toBeNull()
  })
})
