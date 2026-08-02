import type { Paginated } from '~/types/api'
import { unwrapList } from '~/types/api'
import type {
  AdminUser,
  AdminUserPatch,
  AuditEventRecord,
  ReferenceDataItem,
  ReferenceDataType,
} from '~/types/control'

/** Administration endpoints (FR-025 read, FR-026, FR-027). Admin-only. */
export function useAdminService() {
  const api = useApi()

  return {
    /* Users (FR-027) */
    listUsers: (params: Record<string, string | number | boolean> = {}) =>
      api.get<Paginated<AdminUser>>('/admin/users/', { page: 1, ...params }),

    /** Role/scope/active changes are audited; secrets are never displayed. */
    updateUser: (uuid: string, payload: AdminUserPatch) =>
      api.patch<AdminUser>(`/admin/users/${uuid}/`, payload),

    /* Audit events (FR-025 restricted read) */
    auditEvents: (params: Record<string, string | number> = {}) =>
      api.get<Paginated<AuditEventRecord>>('/admin/audit-events/', { page: 1, ...params }),

    /* Reference data (FR-026; DELETE deactivates in-use rows per BR-004) */
    listReferenceData: async (type: ReferenceDataType): Promise<ReferenceDataItem[]> =>
      unwrapList<ReferenceDataItem>(await api.get<unknown>(`/reference-data/${type}/`)),

    createReferenceData: (type: ReferenceDataType, payload: Record<string, unknown>) =>
      api.post<ReferenceDataItem>(`/reference-data/${type}/`, payload),

    updateReferenceData: (type: ReferenceDataType, uuid: string, payload: Record<string, unknown>) =>
      api.patch<ReferenceDataItem>(`/reference-data/${type}/${uuid}/`, payload),

    /** Idempotent deactivate (Rev 1.2 §11.1.10): never destroys rows. */
    deactivateReferenceData: (type: ReferenceDataType, uuid: string) =>
      api.del<{ active: boolean }>(`/reference-data/${type}/${uuid}/`),

    /** Status transition rules (read-only display; configured server-side). */
    transitionRules: async (): Promise<unknown[]> =>
      unwrapList(await api.get<unknown>('/reference-data/transition-rules/')),
  }
}
