import type { ConditionRef, HistoryEvent, Money, NamedRef } from '~/types/api'

/** Cycle-2 workflow contract types (design §10/§11.3). */

export interface PersonRef {
  uuid: string
  display_name: string
}

export interface AssignPayload {
  custodian?: string
  department?: string
  location?: string
  expected_return_at?: string | null
  notes?: string
  requires_acknowledgement?: boolean
}

export interface TransferPayload {
  to_custodian?: string
  to_department?: string
  to_location?: string
  reason: string
  notes?: string
}

export interface ReturnPayload {
  condition?: string
  destination_location?: string
  notes?: string
  damaged?: boolean
}

export interface ReservePayload {
  start_at: string
  end_at: string
  purpose?: string
}

export interface ExceptionPayload {
  exception_type: 'lost' | 'stolen' | 'missing' | 'damaged'
  note: string
}

export interface AssignmentRecord {
  uuid: string
  asset: string
  custodian: PersonRef | null
  department: NamedRef | null
  location: NamedRef | null
  assigned_at: string
  expected_return_at: string | null
  returned_at: string | null
  status: string
  notes?: string
}

export interface MaintenanceRecord {
  uuid: string
  asset: { uuid: string; tag: string; name: string } | string
  type: NamedRef | null
  issue: string
  provider: string
  technician?: string
  started_at: string | null
  completed_at: string | null
  cost?: Money | null
  result: string
  next_due: string | null
  is_open?: boolean
  created_at?: string
}

export interface MaintenanceCreatePayload {
  asset: string
  type?: string
  issue: string
  provider?: string
  started_at?: string | null
  cost?: Money | null
  next_due?: string | null
}

export interface MaintenanceCompletePayload {
  completed_at?: string | null
  result?: string
  next_due?: string | null
}

export interface AttachmentMeta {
  uuid: string
  filename: string
  content_type: string
  size: number
  purpose?: string
  uploaded_by?: string
  uploaded_at: string
  download_url?: string
}

export interface NoteRecord {
  uuid: string
  author: string
  body: string
  created_at: string
}

export type ImportJobStatus =
  | 'queued'
  | 'validating'
  | 'validated'
  | 'processing'
  | 'completed'
  | 'failed'
  | 'expired'

export interface ImportPreviewRow {
  row: number
  status: 'valid' | 'warning' | 'error' | 'duplicate'
  messages: string[]
  data?: Record<string, string>
}

export interface ImportPreview {
  total: number
  valid: number
  warnings: number
  errors: number
  duplicates: number
  rows: ImportPreviewRow[]
}

export interface ImportJob {
  uuid: string
  status: ImportJobStatus
  filename?: string
  created_at: string
  updated_at?: string
  counts?: { created: number; updated: number; skipped: number; failed: number }
  preview?: ImportPreview | null
  error?: string | null
  correlation_id?: string
}

export interface ExportJob {
  uuid: string
  status: 'queued' | 'processing' | 'completed' | 'failed' | 'expired'
  created_at: string
  completed_at?: string | null
  filters?: Record<string, string>
  error?: string | null
}

export type StocktakeOutcome =
  | 'found'
  | 'not_found'
  | 'unexpected'
  | 'duplicate'
  | 'moved'
  | 'condition_mismatch'

export interface StocktakeObservation {
  uuid: string
  asset: { uuid: string; tag: string; name: string } | null
  tag_scanned: string
  operator?: string
  observed_at: string
  location?: NamedRef | null
  condition?: ConditionRef | null
  note?: string
  outcome: StocktakeOutcome | string
}

export interface StocktakeSession {
  uuid: string
  name: string
  status: string
  locations: NamedRef[]
  start_date: string | null
  due_date: string | null
  instructions?: string
  snapshot_at?: string | null
  progress?: Record<string, number>
  observations?: StocktakeObservation[]
  created_at?: string
}

export interface StocktakeCreatePayload {
  name: string
  location_uuids?: string[]
  start_date?: string | null
  due_date?: string | null
  instructions?: string
}

export interface StocktakeObservationPayload {
  tag_scanned: string
  location?: string
  condition?: string
  note?: string
}

export interface VarianceRow {
  uuid?: string
  asset: { uuid: string; tag: string; name: string } | null
  tag_scanned?: string
  outcome: string
  expected_location?: NamedRef | null
  observed_location?: NamedRef | null
  note?: string
}

/** Combined activity feed event (superset of HistoryEvent where documented). */
export type ActivityEvent = HistoryEvent
