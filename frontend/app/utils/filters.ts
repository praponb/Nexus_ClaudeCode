/** Asset register filter/sort/pagination state, serialized to URL query params. */

import type { SavedViewConfig } from '~/types/api'

export const DEFAULT_PAGE_SIZE = 25
export const MAX_PAGE_SIZE = 100

export interface AssetListFilters {
  q: string
  category: string
  status: string
  condition: string
  department: string
  location: string
  ordering: string
  page: number
  pageSize: number
  /**
   * Backend `record_status` filter (active/archived). The register exposes no
   * control for it, so it never appears as a chip -- but saved views may carry
   * it (the seeded "All active assets" view does), and dropping it silently
   * would change what such a view means. Carried through URL -> API unchanged.
   */
  recordStatus: string
}

/** Filter dimensions shown as removable chips (excludes pagination/sort). */
export const FILTER_DIMENSIONS = ['q', 'category', 'status', 'condition', 'department', 'location'] as const
export type FilterDimension = (typeof FILTER_DIMENSIONS)[number]

export const DEFAULT_FILTERS: AssetListFilters = {
  q: '',
  category: '',
  status: '',
  condition: '',
  department: '',
  location: '',
  ordering: '',
  page: 1,
  pageSize: DEFAULT_PAGE_SIZE,
  recordStatus: '',
}

type QueryValue = string | null | (string | null)[] | undefined
type Query = Record<string, QueryValue>

function first(value: QueryValue): string {
  if (Array.isArray(value)) return value[0] ?? ''
  return value ?? ''
}

function toPositiveInt(value: string, fallback: number, max?: number): number {
  const n = Number.parseInt(value, 10)
  if (Number.isNaN(n) || n < 1) return fallback
  if (max && n > max) return max
  return n
}

export function parseAssetQuery(query: Query): AssetListFilters {
  return {
    q: first(query.q),
    category: first(query.category),
    status: first(query.status),
    condition: first(query.condition),
    department: first(query.department),
    location: first(query.location),
    ordering: first(query.ordering),
    page: toPositiveInt(first(query.page), 1),
    pageSize: toPositiveInt(first(query.page_size), DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE),
    recordStatus: first(query.record_status),
  }
}

/** Serialize to query params, omitting defaults to keep URLs clean and shareable. */
export function serializeAssetFilters(filters: AssetListFilters): Record<string, string> {
  const out: Record<string, string> = {}
  if (filters.q) out.q = filters.q
  if (filters.category) out.category = filters.category
  if (filters.status) out.status = filters.status
  if (filters.condition) out.condition = filters.condition
  if (filters.department) out.department = filters.department
  if (filters.location) out.location = filters.location
  if (filters.ordering) out.ordering = filters.ordering
  if (filters.page > 1) out.page = String(filters.page)
  if (filters.pageSize !== DEFAULT_PAGE_SIZE) out.page_size = String(filters.pageSize)
  if (filters.recordStatus) out.record_status = filters.recordStatus
  return out
}

export function activeFilterCount(filters: AssetListFilters): number {
  return FILTER_DIMENSIONS.filter((key) => Boolean(filters[key])).length
}

export function hasActiveFilters(filters: AssetListFilters): boolean {
  return activeFilterCount(filters) > 0
}

/** Query params sent to the backend list endpoint (design D-09 conventions). */
export function toApiParams(filters: AssetListFilters): Record<string, string | number> {
  const params: Record<string, string | number> = {
    page: filters.page,
    page_size: filters.pageSize,
  }
  if (filters.q) params.q = filters.q
  if (filters.category) params.category = filters.category
  if (filters.status) params.status = filters.status
  if (filters.condition) params.condition = filters.condition
  if (filters.department) params.department = filters.department
  if (filters.location) params.location = filters.location
  if (filters.ordering) params.ordering = filters.ordering
  if (filters.recordStatus) params.record_status = filters.recordStatus
  return params
}

/* --- Saved views (FR-006) ------------------------------------------------
 * A saved view is stored in the backend's nested shape
 * (`{filters: {...}, ordering, columns, page_size}`), which is deliberately
 * different from the flat URL/query shape the register uses. These two
 * functions are the only place that translation happens -- keep them
 * inverses of each other.
 * ------------------------------------------------------------------------ */

/** Register state -> stored view config. Pagination is intentionally not saved:
 *  a view describes *which* assets, not which page of them you were on. */
export function toSavedViewConfig(filters: AssetListFilters): SavedViewConfig {
  const stored: Record<string, string> = {}
  if (filters.q) stored.q = filters.q
  if (filters.category) stored.category = filters.category
  if (filters.status) stored.status = filters.status
  if (filters.condition) stored.condition = filters.condition
  if (filters.department) stored.department = filters.department
  if (filters.location) stored.location = filters.location
  if (filters.recordStatus) stored.record_status = filters.recordStatus

  const config: SavedViewConfig = { filters: stored }
  if (filters.ordering) config.ordering = filters.ordering
  if (filters.pageSize !== DEFAULT_PAGE_SIZE) config.page_size = filters.pageSize
  return config
}

/** Stored view config -> register query params. Tolerant of configs written by
 *  other clients or seed data: non-string filter values are skipped rather than
 *  stringified into a URL (which is how `?filters=[object Object]` happened). */
export function savedViewConfigToQuery(config: SavedViewConfig | null | undefined): Record<string, string> {
  const query: Record<string, string> = {}
  if (!config || typeof config !== 'object') return query

  const filters = config.filters
  if (filters && typeof filters === 'object' && !Array.isArray(filters)) {
    for (const [key, value] of Object.entries(filters)) {
      if (typeof value === 'string' && value !== '') query[key] = value
      else if (typeof value === 'number' || typeof value === 'boolean') query[key] = String(value)
    }
  }

  if (typeof config.ordering === 'string' && config.ordering) query.ordering = config.ordering
  if (typeof config.page_size === 'number' && config.page_size !== DEFAULT_PAGE_SIZE) {
    query.page_size = String(config.page_size)
  }
  return query
}
