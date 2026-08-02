import { describe, expect, it } from 'vitest'
import { normalizeTreatment, treatmentForStatus } from '~/utils/status'

describe('treatmentForStatus', () => {
  it('prefers the backend semantic treatment when provided', () => {
    const style = treatmentForStatus('assigned', 'danger')
    expect(style.treatment).toBe('danger')
    expect(style.icon).toBe('error')
  })

  it.each([
    ['available', 'success'],
    ['assigned', 'success'],
    ['in_transit', 'info'],
    ['reserved', 'info'],
    ['maintenance_due', 'warning'],
    ['overdue', 'warning'],
    ['lost', 'danger'],
    ['stolen', 'danger'],
    ['retired', 'neutral'],
    ['disposed', 'neutral'],
  ])('maps status code %s to %s treatment', (code, treatment) => {
    expect(treatmentForStatus(code).treatment).toBe(treatment)
  })

  it('falls back to neutral for unknown codes', () => {
    const style = treatmentForStatus('something_custom')
    expect(style.treatment).toBe('neutral')
    expect(style.icon).toBe('neutral')
  })
})

describe('normalizeTreatment', () => {
  it('accepts known treatments case-insensitively', () => {
    expect(normalizeTreatment('Success')).toBe('success')
    expect(normalizeTreatment('warning')).toBe('warning')
  })

  it('rejects unknown values', () => {
    expect(normalizeTreatment('sparkly')).toBeNull()
    expect(normalizeTreatment(null)).toBeNull()
  })
})
