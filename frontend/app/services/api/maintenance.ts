import type { Paginated } from '~/types/api'
import type {
  MaintenanceCompletePayload,
  MaintenanceCreatePayload,
  MaintenanceRecord,
} from '~/types/workflow'
import { newCorrelationId } from '~/utils/correlation'

export function useMaintenanceService() {
  const api = useApi()

  return {
    list: (params: Record<string, string | number | boolean> = {}) =>
      api.get<Paginated<MaintenanceRecord>>('/maintenance/', {
        page: 1,
        ...params,
      }),

    create: (payload: MaintenanceCreatePayload) =>
      api.post<MaintenanceRecord>('/maintenance/', payload, {
        headers: { 'Idempotency-Key': newCorrelationId() },
      }),

    retrieve: (uuid: string) => api.get<MaintenanceRecord>(`/maintenance/${uuid}/`),

    update: (uuid: string, payload: Partial<MaintenanceCreatePayload>) =>
      api.patch<MaintenanceRecord>(`/maintenance/${uuid}/`, payload),

    complete: (uuid: string, payload: MaintenanceCompletePayload) =>
      api.post<MaintenanceRecord>(`/maintenance/${uuid}/complete/`, payload, {
        headers: { 'Idempotency-Key': newCorrelationId() },
      }),
  }
}
