import type { IconName } from '~/utils/icons'
import type { Role } from '~/types/api'

export interface NavItem {
  to: string
  label: string
  icon: IconName
  /** Roles that may see the item; omitted = every authenticated user. */
  roles?: Role[]
  /** Match only the exact path (used for the dashboard root). */
  exact?: boolean
  /** Marks modules delivered in later cycles (rendered as accessible stubs). */
  planned?: boolean
}

const OPERATOR_UP: Role[] = ['system_admin', 'asset_manager', 'operator']
const MANAGER_UP: Role[] = ['system_admin', 'asset_manager', 'department_manager']

export const PRIMARY_NAV: NavItem[] = [
  { to: '/', label: 'Dashboard', icon: 'dashboard', exact: true },
  { to: '/assets', label: 'Assets', icon: 'cube' },
  { to: '/assignments', label: 'Assignments', icon: 'tasks', roles: OPERATOR_UP },
  { to: '/reservations', label: 'Reservations', icon: 'clock', roles: OPERATOR_UP },
  { to: '/stocktakes', label: 'Stocktakes', icon: 'check', roles: [...OPERATOR_UP, 'department_manager'] },
  { to: '/maintenance', label: 'Maintenance', icon: 'wrench', roles: OPERATOR_UP },
  { to: '/imports', label: 'Imports & exports', icon: 'archive', roles: OPERATOR_UP },
  { to: '/scan', label: 'Scan', icon: 'scan', roles: [...OPERATOR_UP, 'employee'] },
  { to: '/reports', label: 'Reports', icon: 'chart', roles: [...MANAGER_UP, 'auditor'] },
  { to: '/approvals', label: 'Approvals', icon: 'success', roles: MANAGER_UP },
  { to: '/notifications', label: 'Notifications', icon: 'bell' },
  { to: '/admin', label: 'Administration', icon: 'cog', roles: ['system_admin'] },
  { to: '/help', label: 'Help', icon: 'help' },
]

export const BOTTOM_NAV: NavItem[] = [
  { to: '/', label: 'Home', icon: 'home', exact: true },
  { to: '/assets', label: 'Assets', icon: 'cube' },
  { to: '/scan', label: 'Scan', icon: 'scan', roles: [...OPERATOR_UP, 'employee'] },
  { to: '/assignments', label: 'Tasks', icon: 'tasks', roles: OPERATOR_UP },
]

export function navForRole(items: NavItem[], role: Role | null): NavItem[] {
  return items.filter((item) => !item.roles || (role !== null && item.roles.includes(role)))
}

export function isActivePath(item: NavItem, path: string): boolean {
  if (item.exact) return path === item.to
  return path === item.to || path.startsWith(`${item.to}/`)
}
