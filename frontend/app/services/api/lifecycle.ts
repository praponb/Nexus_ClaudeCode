import type { AssetDetail } from '~/types/api'
import type { DisposePayload, ReopenPayload, RetirePayload } from '~/types/control'
import type {
  AssignPayload,
  AssignmentRecord,
  ExceptionPayload,
  ReservePayload,
  ReturnPayload,
  TransferPayload,
} from '~/types/workflow'
import { newCorrelationId } from '~/utils/correlation'

/**
 * Lifecycle transition endpoints (design §11.3).
 * All transitions are unsafe, retry-sensitive POSTs → Idempotency-Key (D-08),
 * and the UI must await the confirmed response before showing success (§14.6).
 */
export function useLifecycleService() {
  const api = useApi()

  function headers(key?: string): Record<string, string> {
    return { 'Idempotency-Key': key ?? newCorrelationId() }
  }

  return {
    assign: (uuid: string, payload: AssignPayload, key?: string) =>
      api.post<AssignmentRecord>(`/assets/${uuid}/assign/`, payload, { headers: headers(key) }),

    transfer: (uuid: string, payload: TransferPayload, key?: string) =>
      api.post<AssetDetail>(`/assets/${uuid}/transfer/`, payload, { headers: headers(key) }),

    returnAsset: (uuid: string, payload: ReturnPayload, key?: string) =>
      api.post<AssetDetail>(`/assets/${uuid}/return/`, payload, { headers: headers(key) }),

    reserve: (uuid: string, payload: ReservePayload, key?: string) =>
      api.post<unknown>(`/assets/${uuid}/reserve/`, payload, { headers: headers(key) }),

    checkout: (uuid: string, payload: Record<string, string> = {}, key?: string) =>
      api.post<unknown>(`/assets/${uuid}/checkout/`, payload, { headers: headers(key) }),

    reportException: (uuid: string, payload: ExceptionPayload, key?: string) =>
      api.post<AssetDetail>(`/assets/${uuid}/report-exception/`, payload, {
        headers: headers(key),
      }),

    /* ---- Cycle 3: retirement / disposal / reopen (FR-014, J-5) ---- */

    retire: (uuid: string, payload: RetirePayload, key?: string) =>
      api.post<AssetDetail>(`/assets/${uuid}/retire/`, payload, { headers: headers(key) }),

    /** BR-006 blockers → 409 DISPOSAL_BLOCKED listing the blockers. */
    dispose: (uuid: string, payload: DisposePayload, key?: string) =>
      api.post<AssetDetail>(`/assets/${uuid}/dispose/`, payload, { headers: headers(key) }),

    /** Reopen a retired/disposed asset: elevated permission + recorded justification. */
    reopen: (uuid: string, payload: ReopenPayload, key?: string) =>
      api.post<AssetDetail>(`/assets/${uuid}/reopen/`, payload, { headers: headers(key) }),
  }
}
