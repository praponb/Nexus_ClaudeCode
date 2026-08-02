import type { Role } from '~/types/api'

/**
 * Permission-driven UI helpers (design §14 rule 7). These hide actions for
 * usability only — the backend re-enforces every authorization decision.
 */
export function usePermissions() {
  const { user } = useAuth()

  const role = computed<Role | null>(() => user.value?.role ?? null)

  function hasRole(...roles: Role[]): boolean {
    return role.value !== null && roles.includes(role.value)
  }

  function can(capability: string): boolean {
    return Boolean(user.value?.capabilities?.includes(capability))
  }

  /** Operator+ may register/edit assets. */
  const canManageAssets = computed(() => hasRole('system_admin', 'asset_manager', 'operator'))
  /** Financial fields restricted to roles with finance.view (design §9.3). */
  const canViewFinance = computed(
    () => can('finance.view') || hasRole('system_admin', 'asset_manager', 'auditor'),
  )
  const isAdmin = computed(() => hasRole('system_admin'))
  const canApprove = computed(() => hasRole('system_admin', 'asset_manager', 'department_manager'))
  const isAuditor = computed(() => hasRole('auditor'))

  return { role, hasRole, can, canManageAssets, canViewFinance, isAdmin, canApprove, isAuditor }
}
