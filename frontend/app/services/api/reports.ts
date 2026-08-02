import { unwrapList } from '~/types/api'
import type { ReportDefinition, ReportResult } from '~/types/control'

/** Reports catalog + viewer endpoints (FR-021). */
export function useReportsService() {
  const api = useApi()

  return {
    /** Catalog may be a bare array or a paginated envelope (Rev 1.1 §11.1.7). */
    catalog: async (): Promise<ReportDefinition[]> =>
      unwrapList<ReportDefinition>(await api.get<unknown>('/reports/')),

    run: (type: string, params: Record<string, string> = {}) =>
      api.get<ReportResult>(`/reports/${encodeURIComponent(type)}/`, params),

    /**
     * Export when authorized. The backend may return a queued job reference
     * or the report payload; the page handles both without claiming success
     * before the confirmed response (design §14.6).
     */
    exportReport: (type: string, params: Record<string, string> = {}) =>
      api.post<unknown>(`/reports/${encodeURIComponent(type)}/export/`, params),
  }
}
