"""Shared pytest fixtures.

The backend test suite requires Django/DRF/PostgreSQL (Docker compose or CI).
In bare environments without Django installed, every Django test module skips
cleanly via ``pytest.importorskip`` so collection never errors.

``DJANGO_SETTINGS_MODULE`` is pinned to ``config.settings.test`` via
pyproject.toml (pytest ini) so pytest-django bootstraps Django before
collection; the env fallback below is a safety net for direct invocations.
"""

import importlib.util
import os
from types import SimpleNamespace

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.test")

import pytest  # noqa: E402

HAS_DJANGO = importlib.util.find_spec("django") is not None

# Test-only credential constant; never a real secret.
TEST_PASSWORD = "cycle1-test-password"

if HAS_DJANGO:

    @pytest.fixture
    def api_client():
        from rest_framework.test import APIClient

        return APIClient()

    @pytest.fixture
    def reference(db):
        from apps.reference_data.models import (
            AssetCondition,
            AssetStatus,
            Category,
            Department,
            Location,
            StatusTransitionRule,
            Supplier,
        )

        draft = AssetStatus.objects.create(code="draft", label="Draft", sort_order=0)
        in_stock = AssetStatus.objects.create(code="in_stock", label="In Stock", sort_order=1)
        assigned = AssetStatus.objects.create(code="assigned", label="Assigned", sort_order=2)
        disposed = AssetStatus.objects.create(
            code="disposed", label="Disposed", sort_order=3, is_terminal=True
        )
        StatusTransitionRule.objects.create(from_status=draft, to_status=in_stock, allowed_roles=[])
        StatusTransitionRule.objects.create(
            from_status=in_stock, to_status=assigned, allowed_roles=[]
        )
        condition = AssetCondition.objects.create(code="good", label="Good")
        category = Category.objects.create(code="laptop", name="Laptop")
        department = Department.objects.create(code="eng", name="Engineering")
        other_department = Department.objects.create(code="fin", name="Finance")
        location = Location.objects.create(code="hq", name="HQ")
        supplier = Supplier.objects.create(code="acme", name="Acme Corp")
        return SimpleNamespace(
            draft=draft,
            in_stock=in_stock,
            assigned=assigned,
            disposed=disposed,
            condition=condition,
            category=category,
            department=department,
            other_department=other_department,
            location=location,
            supplier=supplier,
        )

    @pytest.fixture
    def workflow_reference(reference):
        """Extend base reference data with the statuses, transition rules,
        conditions, and maintenance types the Cycle-2 workflows exercise."""
        from apps.reference_data.models import (
            AssetCondition,
            AssetStatus,
            MaintenanceType,
            StatusTransitionRule,
        )

        statuses = {}
        for code, label, order in [
            ("available", "Available", 10),
            ("in_transit", "In Transit", 11),
            ("under_maintenance", "Under Maintenance", 12),
            ("lost", "Lost", 13),
            ("stolen", "Stolen", 14),
            ("missing", "Missing", 15),
        ]:
            statuses[code] = AssetStatus.objects.create(code=code, label=label, sort_order=order)
        lookup = {
            "in_stock": reference.in_stock,
            "assigned": reference.assigned,
            **statuses,
        }
        for from_code, to_code in [
            ("assigned", "available"),
            ("in_stock", "in_transit"),
            ("in_transit", "available"),
            ("in_transit", "assigned"),
            ("in_stock", "under_maintenance"),
            ("under_maintenance", "available"),
            ("under_maintenance", "assigned"),
            ("in_stock", "lost"),
            ("in_stock", "stolen"),
            ("in_stock", "missing"),
            ("lost", "available"),
            ("stolen", "available"),
            ("missing", "available"),
        ]:
            StatusTransitionRule.objects.create(
                from_status=lookup[from_code], to_status=lookup[to_code], allowed_roles=[]
            )
        reference.statuses = statuses
        reference.damaged = AssetCondition.objects.create(code="damaged", label="Damaged")
        reference.repair = MaintenanceType.objects.create(code="repair", name="Repair")
        return reference

    @pytest.fixture
    def disposal_reference(workflow_reference):
        """Add the retired status and retirement/disposal transition rules
        (FR-014) to the workflow reference data."""
        from apps.reference_data.models import AssetStatus, StatusTransitionRule

        retired = AssetStatus.objects.create(code="retired", label="Retired", sort_order=16)
        lookup = {
            "in_stock": workflow_reference.in_stock,
            "assigned": workflow_reference.assigned,
            "retired": retired,
            "disposed": workflow_reference.disposed,
        }
        for from_code, to_code in [
            ("in_stock", "retired"),
            ("retired", "disposed"),
            ("in_stock", "disposed"),
            ("assigned", "disposed"),
        ]:
            StatusTransitionRule.objects.create(
                from_status=lookup[from_code], to_status=lookup[to_code], allowed_roles=[]
            )
        workflow_reference.retired = retired
        return workflow_reference

    @pytest.fixture
    def make_user(db):
        from apps.accounts.models import User, UserScope

        def _make(username, role, scope_department=None, department=None):
            user = User.objects.create_user(
                username=username, password=TEST_PASSWORD, role=role, department=department
            )
            if scope_department is not None:
                UserScope.objects.create(
                    user=user, scope_type="department", department=scope_department
                )
            return user

        return _make

    @pytest.fixture
    def make_asset(db, reference):
        from apps.assets.models import Asset

        def _make(tag, **kwargs):
            defaults = {
                "name": f"Asset {tag}",
                "category": reference.category,
                "status": reference.in_stock,
                "condition": reference.condition,
                "department": reference.department,
                "location": reference.location,
            }
            defaults.update(kwargs)
            return Asset.objects.create(tag=tag, **defaults)

        return _make

    @pytest.fixture
    def authed(api_client):
        """Return a client force-authenticated as the given user."""

        def _authed(user):
            api_client.force_authenticate(user)
            return api_client

        return _authed
