/** Asset register filter/sort/pagination state, serialized to URL query params. */

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
  return params
}
