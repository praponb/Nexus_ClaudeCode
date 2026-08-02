import { describe, expect, it } from 'vitest'
import { formatBytes, isPastDate } from '~/utils/format'

describe('formatBytes', () => {
  it('formats bytes, KB, and MB', () => {
    expect(formatBytes(512)).toBe('512 B')
    expect(formatBytes(2048)).toBe('2 KB')
    expect(formatBytes(5 * 1024 * 1024)).toBe('5 MB')
  })

  it('guards invalid input', () => {
    expect(formatBytes(undefined)).toBe('—')
    expect(formatBytes(-5)).toBe('—')
  })
})

describe('isPastDate', () => {
  it('detects past and future dates', () => {
    expect(isPastDate('2000-01-01')).toBe(true)
    expect(isPastDate('2999-01-01')).toBe(false)
  })

  it('handles missing and invalid values', () => {
    expect(isPastDate(null)).toBe(false)
    expect(isPastDate('not-a-date')).toBe(false)
  })
})
