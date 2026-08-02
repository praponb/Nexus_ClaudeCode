import type { Paginated } from '~/types/api'
import type { AppNotification, NotificationPreference } from '~/types/control'

export interface NotificationPreferencesState {
  preferences: NotificationPreference[]
}

/**
 * Backend contract (apps/notifications/views.py) is a mute-list model, not
 * a per-type preference list: GET returns
 * `{muted_types, optional_types, mandatory_types}` (flat type-code arrays,
 * no labels/descriptions, no persisted email toggle -- SMTP dispatch is a
 * documented backlog item), and PATCH expects `{muted_types: string[]}`.
 * This service adapts that into the richer NotificationPreference[] shape
 * the UI works with.
 */
interface NotificationPreferencesPayload {
  muted_types: string[]
  optional_types: string[]
  mandatory_types: string[]
}

/** Notification center endpoints (FR-023). */
export function useNotificationsService() {
  const api = useApi()

  return {
    list: (params: Record<string, string | number | boolean> = {}) =>
      api.get<Paginated<AppNotification>>('/notifications/', { page: 1, ...params }),

    markRead: (uuid: string) =>
      api.post<AppNotification>(`/notifications/${uuid}/read/`, {}),

    preferences: async (): Promise<NotificationPreferencesState> => {
      const res = await api.get<NotificationPreferencesPayload>('/notifications/preferences/')
      const muted = new Set(res.muted_types ?? [])
      const mandatory = new Set(res.mandatory_types ?? [])
      const types = [...(res.optional_types ?? []), ...(res.mandatory_types ?? [])]
      return {
        preferences: types.map((type) => ({
          type,
          enabled: !muted.has(type),
          mandatory: mandatory.has(type),
        })),
      }
    },

    updatePreferences: (payload: {
      preferences: Array<Pick<NotificationPreference, 'type' | 'enabled' | 'mandatory'>>
    }) => {
      const muted_types = payload.preferences
        .filter((p) => !p.mandatory && !p.enabled)
        .map((p) => p.type)
      return api.patch<unknown>('/notifications/preferences/', { muted_types })
    },
  }
}
