import type { Paginated } from '~/types/api'
import type {
  StocktakeCreatePayload,
  StocktakeObservation,
  StocktakeObservationPayload,
  StocktakeSession,
  VarianceRow,
} from '~/types/workflow'
import { unwrapList } from '~/types/api'
import { newCorrelationId } from '~/utils/correlation'

export function useStocktakeService() {
  const api = useApi()

  return {
    list: (params: Record<string, string | number> = {}) =>
      api.get<Paginated<StocktakeSession>>('/stocktakes/', { page: 1, ...params }),

    create: (payload: StocktakeCreatePayload) =>
      api.post<StocktakeSession>('/stocktakes/', payload, {
        headers: { 'Idempotency-Key': newCorrelationId() },
      }),

    retrieve: (uuid: string) => api.get<StocktakeSession>(`/stocktakes/${uuid}/`),

    update: (uuid: string, payload: Partial<StocktakeCreatePayload>) =>
      api.patch<StocktakeSession>(`/stocktakes/${uuid}/`, payload),

    start: (uuid: string) =>
      api.post<StocktakeSession>(`/stocktakes/${uuid}/start/`, {}),

    reconcile: (uuid: string) =>
      api.post<StocktakeSession>(`/stocktakes/${uuid}/reconcile/`, {}),

    close: (uuid: string) =>
      api.post<StocktakeSession>(`/stocktakes/${uuid}/close/`, {}),

    addObservation: (uuid: string, payload: StocktakeObservationPayload) =>
      api.post<StocktakeObservation>(`/stocktakes/${uuid}/observations/`, payload, {
        headers: { 'Idempotency-Key': newCorrelationId() },
      }),

    observations: async (uuid: string) =>
      unwrapList<StocktakeObservation>(
        await api.get<unknown>(`/stocktakes/${uuid}/observations/`),
      ),

    variance: async (uuid: string) =>
      unwrapList<VarianceRow>(await api.get<unknown>(`/stocktakes/${uuid}/variance/`)),
  }
}
