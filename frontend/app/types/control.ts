import type { NamedRef, Role, UserScope } from '~/types/api'

/** Cycle-3 contract types (design Rev 1.2 §10/§11.3). */

export interface AssetRef {
  uuid: string
  tag: string
  name: string
}

export interface PersonRef {
  uuid: string
  display_name: string
}

/* ---- Reservations (FR-010 completion, Rev 1.2) ---- */

export type ReservationStatus =
  | 'requested'
  | 'confirmed'
  | 'checked_out'
  | 'returned'
  | 'cancelled'
  | 'expired'

export interface Reservation {
  uuid: string
  asset: AssetRef | null
  requester: PersonRef | null
  start_at: string
  end_at: string
  purpose?: string
  status: ReservationStatus | string
  is_overdue?: boolean
  created_at?: string
}

/* ---- Approvals (FR-024) ---- */

export type ApprovalStatus = 'pending' | 'approved' | 'rejected' | 'returned'

export interface ApprovalRequest {
  uuid: string
  type: string
  requester: PersonRef | null
  asset: AssetRef | null
  reason?: string
  payload?: Record<string, unknown>
  status: ApprovalStatus | string
  approver?: PersonRef | null
  decided_at?: string | null
  comments?: string
  created_at: string
}

export type ApprovalDecisionAction = 'approve' | 'reject' | 'return'

/* ---- Notifications (FR-023) ---- */

export interface AppNotification {
  uuid: string
  type: string
  title: string
  body: string
  link?: string | null
  read_at: string | null
  created_at: string
}

export interface NotificationPreference {
  type: string
  label?: string
  description?: string
  enabled: boolean
  /** Mandatory compliance notifications cannot be disabled (FR-023). */
  mandatory?: boolean
}

/* ---- Reports (FR-021) ---- */

export interface ReportFilterSpec {
  key: string
  label: string
  type: 'date' | 'text' | 'select'
  options?: { value: string; label: string }[]
}

export interface ReportDefinition {
  type: string
  name: string
  description?: string
  filters?: ReportFilterSpec[]
}

export interface ReportResult {
  type?: string
  name?: string
  generated_at?: string
  /** Column keys in display order; rows are keyed objects. */
  columns?: Array<string | { key: string; label: string }>
  rows: Array<Record<string, unknown>>
  totals?: Record<string, unknown>
}

/* ---- Administration (FR-025 read, FR-027) ---- */

export interface AdminUser {
  uuid: string
  username: string
  display_name: string
  email: string
  role: Role
  active: boolean
  scopes?: UserScope[]
  last_login?: string | null
}

export interface AdminUserPatch {
  role?: Role
  active?: boolean
  display_name?: string
  scopes?: Array<{ scope_type: string; scope: string }>
}

export interface AuditEventRecord {
  uuid?: string
  actor: string
  actor_type?: 'user' | 'service' | string
  action: string
  target_type?: string
  target_uuid?: string
  outcome?: string
  correlation_id?: string
  created_at: string
}

/* ---- Data quality (FR-028) ---- */

export interface DataQualityIssue {
  uuid: string
  asset: AssetRef | null
  rule?: string
  severity: 'error' | 'warning' | string
  message: string
  resolved_at?: string | null
  created_at?: string
}

/* ---- Retirement / disposal (FR-014) ---- */

export interface RetirePayload {
  reason: string
}

export interface DisposePayload {
  method?: string
  reason: string
}

export interface ReopenPayload {
  justification: string
}

/** Reference-data entity types manageable in the admin UI (FR-026). */
export type ReferenceDataType =
  | 'categories'
  | 'statuses'
  | 'conditions'
  | 'departments'
  | 'locations'
  | 'cost-centers'
  | 'suppliers'

export interface ReferenceDataItem extends NamedRef {
  description?: string
  sort_order?: number
}
