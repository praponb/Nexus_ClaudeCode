import { describe, expect, it } from 'vitest'
import { parseScannedTag } from '~/utils/scan'

describe('parseScannedTag', () => {
  it('accepts plain asset tags', () => {
    expect(parseScannedTag('AST-000123')).toBe('AST-000123')
    expect(parseScannedTag('  ast-1  ')).toBe('ast-1')
  })

  it('extracts the tag from app deep links (design D-14)', () => {
    expect(parseScannedTag('https://assets.example.com/scan?tag=AST-000123')).toBe('AST-000123')
    expect(parseScannedTag('/scan?tag=AST-000123')).toBe('AST-000123')
    expect(parseScannedTag('http://localhost:3000/scan?foo=1&tag=XYZ-9&other=2')).toBe('XYZ-9')
  })

  it('rejects URLs without a tag parameter', () => {
    expect(parseScannedTag('https://example.com/phishing')).toBeNull()
    expect(parseScannedTag('/assets/some-page')).toBeNull()
  })

  it('rejects empty and implausible values', () => {
    expect(parseScannedTag('')).toBeNull()
    expect(parseScannedTag('   ')).toBeNull()
    expect(parseScannedTag('not a tag!')).toBeNull()
  })
})
