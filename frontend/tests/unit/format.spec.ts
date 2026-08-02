import { describe, expect, it } from 'vitest'
import { formatCount, formatDate, formatDateTime, formatMoney } from '~/utils/format'

describe('formatMoney', () => {
  it('formats decimal-string money without float math (D-06)', () => {
    expect(formatMoney({ amount: '1299.99', currency: 'USD' })).toContain('1,299.99')
  })

  it('renders a dash for missing values', () => {
    expect(formatMoney(null)).toBe('—')
    expect(formatMoney({ amount: '', currency: 'USD' })).toBe('—')
  })

  it('degrades gracefully for unknown currencies', () => {
    expect(formatMoney({ amount: '10', currency: 'XXX-invalid' })).toBe('10 XXX-invalid')
  })
})

describe('date formatting', () => {
  it('formats ISO datetimes and guards invalid input', () => {
    expect(formatDate('2025-01-15T10:00:00Z')).not.toBe('—')
    expect(formatDateTime('2025-01-15T10:00:00Z')).not.toBe('—')
    expect(formatDate('not-a-date')).toBe('—')
    expect(formatDate(null)).toBe('—')
  })
})

describe('formatCount', () => {
  it('formats with grouping and guards NaN', () => {
    expect(formatCount(123456)).toBe(new Intl.NumberFormat('en').format(123456))
    expect(formatCount(Number.NaN)).toBe('0')
  })
})
