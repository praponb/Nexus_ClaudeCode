import type { Paginated } from '~/types/api'
import type { Reservation } from '~/types/control'

/** Scoped reservations list (FR-010 completion, Rev 1.2 §11.3). */
export function useReservationsService() {
  const api = useApi()

  return {
    list: (params: Record<string, string | number | boolean> = {}) =>
      api.get<Paginated<Reservation>>('/reservations/', { page: 1, ...params }),
  }
}
