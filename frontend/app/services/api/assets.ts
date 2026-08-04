import type {
  AssetDetail,
  AssetSummary,
  AssetWritePayload,
  DuplicateCheckResponse,
  DuplicateWarning,
  HistoryEvent,
  Paginated,
} from '~/types/api'
import type { AttachmentMeta, NoteRecord } from '~/types/workflow'
import { unwrapList } from '~/types/api'
import { newCorrelationId } from '~/utils/correlation'

export interface CreateAssetResponse {
  asset: AssetDetail
  /** Same duplicate-warning objects the check-duplicates endpoint returns. */
  warnings: DuplicateWarning[]
}

/** Typed asset endpoints (design §11.3; DRF trailing slashes per Rev 1.1 §11.1). */
export function useAssetsService() {
  const api = useApi()

  return {
    list: (params: Record<string, string | number>) =>
      api.get<Paginated<AssetSummary>>('/assets/', params),

    retrieve: (uuid: string) => api.get<AssetDetail>(`/assets/${uuid}/`),

    /** Create returns 201 { asset, warnings } (Rev 1.1 §11.1 item 2). */
    create: async (
      payload: AssetWritePayload,
      idempotencyKey: string = newCorrelationId(),
    ): Promise<CreateAssetResponse> => {
      const res = await api.post<CreateAssetResponse | AssetDetail>('/assets/', payload, {
        headers: { 'Idempotency-Key': idempotencyKey },
      })
      if (res && typeof res === 'object' && 'asset' in res) {
        const envelope = res as CreateAssetResponse
        return { asset: envelope.asset, warnings: envelope.warnings ?? [] }
      }
      return { asset: res as AssetDetail, warnings: [] }
    },

    /** Optimistic concurrency: version in body + If-Match header (design D-07). */
    update: (uuid: string, payload: AssetWritePayload, version: number) =>
      api.patch<AssetDetail>(
        `/assets/${uuid}/`,
        { ...payload, version },
        { headers: { 'If-Match': String(version) } },
      ),

    checkDuplicates: (payload: Partial<AssetWritePayload>, uuid?: string) =>
      api.post<DuplicateCheckResponse>(
        uuid ? `/assets/${uuid}/check-duplicates/` : '/assets/check-duplicates/',
        payload,
      ),

    history: (uuid: string, page = 1) =>
      api.get<Paginated<HistoryEvent>>(`/assets/${uuid}/history/`, { page }),

    /** Full combined activity feed (FR-029, Cycle 2). */
    activity: (uuid: string, page = 1) =>
      api.get<Paginated<HistoryEvent>>(`/assets/${uuid}/activity/`, { page }),

    addNote: (uuid: string, body: string) =>
      api.post<NoteRecord>(`/assets/${uuid}/notes/`, { body }),

    attachments: async (uuid: string) =>
      unwrapList<AttachmentMeta>(await api.get<unknown>(`/assets/${uuid}/attachments/`)),

    uploadAttachment: (uuid: string, file: File, purpose?: string) => {
      const form = new FormData()
      form.append('file', file)
      if (purpose) form.append('purpose', purpose)
      return api.postForm<AttachmentMeta>(`/assets/${uuid}/attachments/`, form)
    },

    deleteAttachment: (uuid: string, attachmentUuid: string) =>
      api.del(`/assets/${uuid}/attachments/${attachmentUuid}/`),

    /** QR label (design D-14): server-rendered SVG markup or a JSON wrapper. */
    label: async (uuid: string): Promise<{ svg: string; deepLink: string }> => {
      const text = await api.getText(`/assets/${uuid}/label/`)
      try {
        const parsed = JSON.parse(text) as { svg?: string; deep_link?: string; url?: string }
        return { svg: parsed.svg ?? text, deepLink: parsed.deep_link ?? parsed.url ?? '' }
      } catch {
        return { svg: text, deepLink: '' }
      }
    },
  }
}
