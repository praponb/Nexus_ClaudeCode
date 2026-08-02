import type { Paginated } from '~/types/api'
import type { DataQualityIssue } from '~/types/control'

/** Data-quality work queue (FR-028): errors vs warnings, resolvable. */
export function useDataQualityService() {
  const api = useApi()

  return {
    issues: (params: Record<string, string | number | boolean> = {}) =>
      api.get<Paginated<DataQualityIssue>>('/data-quality/issues/', { page: 1, ...params }),

    /** Resolution preserves audit history; the issue is never deleted. */
    resolve: (uuid: string, note?: string) =>
      api.post<DataQualityIssue>(`/data-quality/issues/${uuid}/resolve/`, note ? { note } : {}),
  }
}
