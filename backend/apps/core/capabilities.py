"""Role capability map (design section 9.3).

Capabilities are surfaced to the frontend via /auth/me for UI hiding only; the
backend re-enforces authorization on every endpoint.
"""

GLOBAL_READ_ROLES = frozenset({"system_admin", "asset_manager", "auditor", "viewer"})
ASSET_WRITE_ROLES = frozenset({"system_admin", "asset_manager", "operator"})
FINANCE_ROLES = frozenset({"system_admin", "asset_manager", "auditor"})

ROLE_CAPABILITIES: dict[str, list[str]] = {
    "system_admin": [
        "asset.read",
        "asset.create",
        "asset.edit",
        "finance.view",
        "reference.read",
        "reference.admin",
        "user.admin",
        "audit.read",
        "dashboard.view",
        "search",
        "savedview.manage",
        "report.export",
    ],
    "asset_manager": [
        "asset.read",
        "asset.create",
        "asset.edit",
        "finance.view",
        "reference.read",
        "dashboard.view",
        "search",
        "savedview.manage",
        "report.export",
    ],
    "department_manager": [
        "asset.read",
        "reference.read",
        "dashboard.view",
        "search",
        "savedview.manage",
    ],
    "operator": [
        "asset.read",
        "asset.create",
        "asset.edit",
        "reference.read",
        "dashboard.view",
        "search",
        "savedview.manage",
    ],
    "employee": [
        "asset.read",
        "reference.read",
        "dashboard.view",
        "search",
        "savedview.manage",
    ],
    "auditor": [
        "asset.read",
        "finance.view",
        "reference.read",
        "audit.read",
        "dashboard.view",
        "search",
        "report.export",
    ],
    # Read-only role for the public demo: global read of the register, but
    # deliberately no audit.read (AuditEvent stores client IPs), no finance.view,
    # and no write capability -- ASSET_WRITE_ROLES and FINANCE_ROLES both exclude
    # it, so those deny by omission rather than needing new checks.
    "viewer": [
        "asset.read",
        "reference.read",
        "dashboard.view",
        "search",
        "savedview.manage",
        "report.export",
    ],
}


def user_role(user) -> str:
    return getattr(user, "role", "") or ""


def is_global_reader(user) -> bool:
    return user_role(user) in GLOBAL_READ_ROLES


def can_write_assets(user) -> bool:
    return user_role(user) in ASSET_WRITE_ROLES


def can_view_finance(user) -> bool:
    return user_role(user) in FINANCE_ROLES


def is_system_admin(user) -> bool:
    return user_role(user) == "system_admin"


def capabilities_for(user) -> list[str]:
    return list(ROLE_CAPABILITIES.get(user_role(user), []))
