/**
 * API contract types for the v1 backend (detail-design-specification.md §11).
 * These mirror the documented contract; once `backend/openapi.json` is
 * published, generated types can replace the hand-written ones.
 */

export type Role =
  | 'system_admin'
  | 'asset_manager'
  | 'department_manager'
  | 'operator'
  | 'employee'
  | 'auditor'

export interface UserScope {
  scope_type: 'department' | 'location' | 'business_unit'
  uuid: string
  name: string
}

export interface CurrentUser {
  uuid: string
  username: string
  display_name: string
  email: string
  role: Role
  scopes: UserScope[]
  capabilities?: string[]
}

/** Pagination envelope (design D-09). */
export interface Paginated<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

/** Error envelope (design §11.2). */
export interface ApiErrorBody {
  error: {
    code: string
    message: string
    field_errors?: Record<string, string[]>
    correlation_id?: string
    retryable?: boolean
  }
}

export interface NamedRef {
  uuid: string
  name: string
  code?: string
  active?: boolean
}

export interface StatusRef {
  uuid: string
  code: string
  label: string
  semantic_treatment?: string
  icon?: string
}

export interface ConditionRef {
  uuid: string
  code: string
  label: string
  semantic_treatment?: string
}

/** Money representation (design D-06): decimal string + ISO currency. */
export interface Money {
  amount: string
  currency: string
}

export interface AssetSummary {
  uuid: string
  tag: string
  name: string
  category: NamedRef | null
  status: StatusRef | null
  condition: ConditionRef | null
  custodian: { uuid: string; display_name: string } | null
  department: NamedRef | null
  location: NamedRef | null
  updated_at: string
  warnings?: string[]
}

export interface AssetDetail extends AssetSummary {
  description: string
  serial_number: string
  manufacturer: string
  brand: string
  model: string
  acquisition_type: string
  /** Category-specific dynamic fields (design §9.4); keyed by CategoryAttributeDefinition.key. */
  category_attributes: Record<string, unknown>
  purchase_date: string | null
  purchase_price?: Money | null
  supplier: NamedRef | null
  warranty_start: string | null
  warranty_end: string | null
  version: number
  created_at: string
}

/** Payload accepted by POST /assets and PATCH /assets/:uuid. */
export interface AssetWritePayload {
  tag?: string
  name: string
  description?: string
  category: string
  status?: string
  condition?: string
  department?: string
  location?: string
  serial_number?: string
  manufacturer?: string
  brand?: string
  model?: string
  acquisition_type?: string
  category_attributes?: Record<string, unknown>
  purchase_date?: string | null
  purchase_price?: Money | null
  warranty_start?: string | null
  warranty_end?: string | null
}

/** Category attribute schema (apps/reference_data: CategoryAttributeDefinition). */
export interface CategoryAttributeDefinition {
  uuid: string
  key: string
  label: string
  field_type:
    | 'text'
    | 'longtext'
    | 'number'
    | 'decimal'
    | 'currency'
    | 'date'
    | 'datetime'
    | 'bool'
    | 'choice'
    | 'multichoice'
    | 'reference'
  required: boolean
  options: string[]
  unique?: boolean
  restricted?: boolean
}

/** Category reference data, extended with its dynamic attribute schema. */
export interface CategoryRef extends NamedRef {
  attribute_definitions?: CategoryAttributeDefinition[]
}

export interface DuplicateCandidate {
  uuid: string
  tag: string
  name: string
  match_reasons: string[]
}

export interface DuplicateCheckResponse {
  warnings: string[]
  candidates: DuplicateCandidate[]
}

export interface HistoryEvent {
  uuid: string
  type: string
  actor: string
  occurred_at: string
  summary: string
  details?: Record<string, unknown>
}

export interface StatusCount {
  code: string
  label: string
  count: number
}

export interface CategoryCount {
  uuid: string
  name: string
  count: number
}

export interface DashboardSummary {
  total_assets: number
  assigned: number
  unassigned: number
  by_status: StatusCount[]
  by_category: CategoryCount[]
  generated_at: string
}

export interface SavedView {
  uuid: string
  name: string
  config: Record<string, unknown>
  shared: boolean
  is_default: boolean
}

/** List endpoints that may return either a bare array or a paginated envelope. */
export function unwrapList<T>(data: unknown): T[] {
  if (Array.isArray(data)) return data as T[]
  if (data && typeof data === 'object' && 'results' in data) {
    return (data as Paginated<T>).results
  }
  return []
}
