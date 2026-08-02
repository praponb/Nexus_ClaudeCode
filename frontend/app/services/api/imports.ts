import type { Paginated } from '~/types/api'
import type { ImportJob } from '~/types/workflow'
import { newCorrelationId } from '~/utils/correlation'

export interface ImportCommitPayload {
  duplicate_policy: 'reject' | 'update' | 'create'
  allow_partial: boolean
}

export function useImportsService() {
  const api = useApi()

  return {
    list: (params: Record<string, string | number> = {}) =>
      api.get<Paginated<ImportJob>>('/imports/', { page: 1, ...params }),

    /** Multipart CSV upload (FR-018 step 2). */
    upload: (file: File) => {
      const form = new FormData()
      form.append('file', file)
      return api.postForm<ImportJob>('/imports/', form)
    },

    retrieve: (uuid: string) => api.get<ImportJob>(`/imports/${uuid}/`),

    /** Commit is async + idempotent (D-08/D-10). */
    commit: (uuid: string, payload: ImportCommitPayload) =>
      api.post<ImportJob>(`/imports/${uuid}/commit/`, payload, {
        headers: { 'Idempotency-Key': newCorrelationId() },
      }),

    result: (uuid: string) => api.get<ImportJob>(`/imports/${uuid}/result/`),

    /** Template download URL (GET via top-level navigation, session cookie sent). */
    templateUrl: () => `${api.baseURL}/imports/template/`,
  }
}
