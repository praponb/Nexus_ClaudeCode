import { describe, expect, it } from 'vitest'
import { formatReportCell, normalizeColumns, reportCellLink } from '~/utils/report'

describe('normalizeColumns', () => {
  it('uses declared string columns with humanized labels', () => {
    const cols = normalizeColumns({ rows: [], columns: ['asset_tag', 'total_count'] })
    expect(cols).toEqual([
      { key: 'asset_tag', label: 'Asset Tag' },
      { key: 'total_count', label: 'Total Count' },
    ])
  })

  it('uses declared object columns, falling back to humanized keys', () => {
    const cols = normalizeColumns({
      rows: [],
      columns: [{ key: 'tag', label: 'Asset tag' }, { key: 'purchase_price' } as { key: string; label: string }],
    })
    expect(cols[0]).toEqual({ key: 'tag', label: 'Asset tag' })
    expect(cols[1]).toEqual({ key: 'purchase_price', label: 'Purchase Price' })
  })

  it('infers columns from the first row when none are declared', () => {
    const cols = normalizeColumns({ rows: [{ tag: 'AST-1', count: 3 }] })
    expect(cols.map((c) => c.key)).toEqual(['tag', 'count'])
  })

  it('returns no columns for empty or missing results', () => {
    expect(normalizeColumns(null)).toEqual([])
    expect(normalizeColumns({ rows: [] })).toEqual([])
  })
})

describe('formatReportCell', () => {
  it('renders empty values as an em dash', () => {
    expect(formatReportCell(null)).toBe('—')
    expect(formatReportCell(undefined)).toBe('—')
    expect(formatReportCell('')).toBe('—')
  })

  it('renders booleans as Yes/No', () => {
    expect(formatReportCell(true)).toBe('Yes')
    expect(formatReportCell(false)).toBe('No')
  })

  it('renders money objects as decimal string + currency (D-06)', () => {
    expect(formatReportCell({ amount: '1234.56', currency: 'USD' })).toBe('1234.56 USD')
  })

  it('renders reference objects by label, name, or tag', () => {
    expect(formatReportCell({ uuid: 'x', label: 'In Service' })).toBe('In Service')
    expect(formatReportCell({ uuid: 'x', name: 'Laptops' })).toBe('Laptops')
    expect(formatReportCell({ uuid: 'x', tag: 'AST-1' })).toBe('AST-1')
  })

  it('renders arrays and plain values', () => {
    expect(formatReportCell(['a', 'b'])).toBe('a, b')
    expect(formatReportCell(42)).toBe('42')
  })
})

describe('reportCellLink', () => {
  it('links asset-shaped cells to their supporting record', () => {
    expect(reportCellLink({ uuid: 'abc', tag: 'AST-1' })).toBe('/assets/abc')
    expect(reportCellLink({ uuid: 'abc', name: 'Laptop' })).toBe('/assets/abc')
  })

  it('returns null for non-linkable values', () => {
    expect(reportCellLink(null)).toBeNull()
    expect(reportCellLink('AST-1')).toBeNull()
    expect(reportCellLink({ label: 'No uuid' })).toBeNull()
  })
})
