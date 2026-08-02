import type { Paginated } from '~/types/api'
import type { ExportJob } from '~/types/workflow'

export function useExportsService() {
  const api = useApi()

  return {
    list: (params: Record<string, string | number> = {}) =>
      api.get<Paginated<ExportJob>>('/exports/', { page: 1, ...params }),

    create: (filters: Record<string, string>) =>
      api.post<ExportJob>('/exports/', { format: 'csv', filters }),

    retrieve: (uuid: string) => api.get<ExportJob>(`/exports/${uuid}/`),

    download: (uuid: string) => api.getBlob(`/exports/${uuid}/download/`),
  }
}
