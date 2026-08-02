import type { DashboardSummary } from '~/types/api'

/**
 * Dashboard's recent-activity feed is a lighter-weight projection than the
 * full per-asset HistoryEvent (backend: apps/reporting/views.py) -- no
 * actor/uuid/details, and the asset identity is nested. Do not conflate
 * this with HistoryEvent; map explicitly where consumed (see index.vue).
 */
export interface DashboardActivityEvent {
  occurred_at: string
  event_type: string
  summary: string
  asset: { uuid: string; tag: string }
}

/** Cycle-2 dashboard completion: alert/task fields are additive + optional. */
export interface DashboardSummaryExtended extends DashboardSummary {
  overdue_returns?: number
  maintenance_due?: number
  warranty_expiring?: number
  missing?: number
  recent_activity?: DashboardActivityEvent[]
}

export function useDashboardService() {
  const api = useApi()
  return {
    summary: () => api.get<DashboardSummaryExtended>('/dashboard/summary/'),
  }
}
