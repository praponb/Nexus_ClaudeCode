import type { ReportResult } from '~/types/control'
import { codeToLabel } from '~/utils/status'

export interface ReportColumn {
  key: string
  label: string
}

/** Display columns: declared columns win; otherwise infer from the first row. */
export function normalizeColumns(result: ReportResult | null | undefined): ReportColumn[] {
  if (!result) return []
  if (result.columns?.length) {
    return result.columns.map((col) =>
      typeof col === 'string'
        ? { key: col, label: codeToLabel(col) }
        : { key: col.key, label: col.label || codeToLabel(col.key) },
    )
  }
  const first = result.rows[0]
  if (!first) return []
  return Object.keys(first).map((key) => ({ key, label: codeToLabel(key) }))
}

/** Format a report cell: money objects (D-06), refs, booleans, plain values. */
export function formatReportCell(value: unknown): string {
  if (value === null || value === undefined || value === '') return '—'
  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  if (typeof value === 'object') {
    if (Array.isArray(value)) return value.map(formatReportCell).join(', ')
    const v = value as Record<string, unknown>
    if (typeof v.amount === 'string' && typeof v.currency === 'string') return `${v.amount} ${v.currency}`
    if (typeof v.label === 'string') return v.label
    if (typeof v.name === 'string') return v.name
    if (typeof v.tag === 'string') return v.tag
    return JSON.stringify(value)
  }
  return String(value)
}

/** Link a cell to its supporting record when it carries an asset reference. */
export function reportCellLink(value: unknown): string | null {
  if (value && typeof value === 'object' && !Array.isArray(value)) {
    const v = value as Record<string, unknown>
    if (typeof v.uuid === 'string' && (typeof v.tag === 'string' || typeof v.name === 'string')) {
      return `/assets/${v.uuid}`
    }
  }
  return null
}
