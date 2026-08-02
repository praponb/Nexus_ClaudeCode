import { describe, expect, it } from 'vitest'
import { codeToLabel, outcomeStyle } from '~/utils/status'

describe('outcomeStyle (stocktake outcomes, layout §15.2)', () => {
  it.each([
    ['found', 'success'],
    ['moved', 'info'],
    ['duplicate', 'warning'],
    ['unexpected', 'warning'],
    ['condition_mismatch', 'warning'],
    ['not_found', 'danger'],
  ])('maps %s to %s', (outcome, treatment) => {
    expect(outcomeStyle(outcome).treatment).toBe(treatment)
  })

  it('is case and separator tolerant, neutral for unknown', () => {
    expect(outcomeStyle('Condition-Mismatch').treatment).toBe('warning')
    expect(outcomeStyle('whatever').treatment).toBe('neutral')
    expect(outcomeStyle(null).treatment).toBe('neutral')
  })

  it('always provides an icon (never color alone)', () => {
    for (const outcome of ['found', 'moved', 'duplicate', 'not_found']) {
      expect(outcomeStyle(outcome).icon).toBeTruthy()
    }
  })
})

describe('codeToLabel', () => {
  it('humanizes machine codes', () => {
    expect(codeToLabel('condition_mismatch')).toBe('Condition Mismatch')
    expect(codeToLabel('in-transit')).toBe('In Transit')
    expect(codeToLabel('found')).toBe('Found')
  })

  it('handles empty input', () => {
    expect(codeToLabel('')).toBe('Unknown')
    expect(codeToLabel(null)).toBe('Unknown')
  })
})
