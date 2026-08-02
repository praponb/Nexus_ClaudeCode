import type { Paginated } from '~/types/api'
import type { ApprovalDecisionAction, ApprovalRequest } from '~/types/control'

/**
 * Approval inbox endpoints (FR-024). Decisions are immutable after the
 * confirmed response; separation of duties (requester ≠ approver) is
 * enforced by the backend and surfaced via the error envelope.
 */
export function useApprovalsService() {
  const api = useApi()

  return {
    list: (params: Record<string, string | number | boolean> = {}) =>
      api.get<Paginated<ApprovalRequest>>('/approvals/', { page: 1, ...params }),

    decide: (uuid: string, action: ApprovalDecisionAction, comments: string) =>
      api.post<ApprovalRequest>(`/approvals/${uuid}/${action}/`, { comments }),
  }
}
