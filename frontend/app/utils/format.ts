import type { Money } from '~/types/api'

const dateFormatter = new Intl.DateTimeFormat('en', { dateStyle: 'medium' })
const dateTimeFormatter = new Intl.DateTimeFormat('en', {
  dateStyle: 'medium',
  timeStyle: 'short',
})

function toDate(value: string | null | undefined): Date | null {
  if (!value) return null
  const d = new Date(value)
  return Number.isNaN(d.getTime()) ? null : d
}

/** Locale-aware date display; ISO 8601 remains the storage/API format. */
export function formatDate(value: string | null | undefined): string {
  const d = toDate(value)
  return d ? dateFormatter.format(d) : '—'
}

export function formatDateTime(value: string | null | undefined): string {
  const d = toDate(value)
  return d ? dateTimeFormatter.format(d) : '—'
}

/** Money is a decimal string + ISO currency code (design D-06); never float math. */
export function formatMoney(money: Money | null | undefined): string {
  if (!money || money.amount == null || money.amount === '') return '—'
  const amount = Number(money.amount)
  if (Number.isNaN(amount)) return `${money.amount} ${money.currency}`
  try {
    return new Intl.NumberFormat('en', {
      style: 'currency',
      currency: money.currency || 'USD',
    }).format(amount)
  } catch {
    return `${money.amount} ${money.currency}`
  }
}

export function formatCount(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return '0'
  return new Intl.NumberFormat('en').format(value)
}

function humanSize(value: number): string {
  const rounded = Math.round(value * 10) / 10
  return Number.isInteger(rounded) ? String(rounded) : rounded.toFixed(1)
}

/** Human-readable file size for attachment lists. */
export function formatBytes(bytes: number | null | undefined): string {
  if (bytes == null || Number.isNaN(bytes) || bytes < 0) return '—'
  if (bytes < 1024) return `${bytes} B`
  const kb = bytes / 1024
  if (kb < 1024) return `${humanSize(kb)} KB`
  return `${humanSize(kb / 1024)} MB`
}

/** Overdue check for maintenance/warranty dates. */
export function isPastDate(value: string | null | undefined): boolean {
  if (!value) return false
  const d = toDate(value)
  if (!d) return false
  return d.getTime() < Date.now()
}
