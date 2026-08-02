"""Seed non-sensitive development data (design section 10.4).

Idempotent: safe to run repeatedly. Demo passwords come from the
SEED_DEMO_PASSWORD environment variable; if unset, a random password is
generated and printed once to stdout. No real credentials are stored in code.
"""

import os
import random
import secrets
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import UserScope
from apps.assets.models import Asset, LifecycleEvent
from apps.assignments.models import Assignment
from apps.reference_data.models import (
    AssetCondition,
    AssetStatus,
    Category,
    CategoryAttributeDefinition,
    CostCenter,
    Department,
    Location,
    StatusTransitionRule,
    Supplier,
)
from apps.reporting.models import SavedView

STATUSES = [
    ("draft", "Draft", "pencil", "neutral", 0, False),
    ("ordered", "Ordered", "shopping-cart", "info", 1, False),
    ("in_stock", "In Stock", "box", "info", 2, False),
    ("available", "Available", "check-circle", "success", 3, False),
    ("reserved", "Reserved", "bookmark", "warning", 4, False),
    ("assigned", "Assigned", "user-check", "info", 5, False),
    ("in_transit", "In Transit", "truck", "warning", 6, False),
    ("under_maintenance", "Under Maintenance", "wrench", "warning", 7, False),
    ("missing", "Missing", "alert-triangle", "danger", 8, False),
    ("lost", "Lost", "x-circle", "danger", 9, False),
    ("stolen", "Stolen", "shield-off", "danger", 10, False),
    ("retired", "Retired", "archive", "neutral", 11, False),
    ("disposed", "Disposed", "trash-2", "neutral", 12, True),
]

CONDITIONS = [
    ("new", "New", "sparkles", "success", 0),
    ("good", "Good", "thumbs-up", "success", 1),
    ("fair", "Fair", "minus-circle", "warning", 2),
    ("damaged", "Damaged", "alert-triangle", "danger", 3),
    ("unserviceable", "Unserviceable", "x-octagon", "danger", 4),
    ("unknown", "Unknown", "help-circle", "neutral", 5),
]

TRANSITION_PAIRS = [
    ("draft", "in_stock"),
    ("draft", "ordered"),
    ("ordered", "in_stock"),
    ("in_stock", "available"),
    ("in_stock", "assigned"),
    ("in_stock", "in_transit"),
    ("in_stock", "retired"),
    ("in_stock", "missing"),
    ("in_stock", "lost"),
    ("in_stock", "stolen"),
    ("available", "reserved"),
    ("available", "assigned"),
    ("available", "under_maintenance"),
    ("available", "in_transit"),
    ("available", "retired"),
    ("available", "missing"),
    ("available", "lost"),
    ("available", "stolen"),
    ("reserved", "available"),
    ("reserved", "assigned"),
    ("assigned", "available"),
    ("assigned", "in_transit"),
    ("assigned", "under_maintenance"),
    ("assigned", "missing"),
    ("assigned", "lost"),
    ("assigned", "stolen"),
    ("assigned", "retired"),
    ("in_transit", "assigned"),
    ("in_transit", "available"),
    ("under_maintenance", "available"),
    ("under_maintenance", "assigned"),
    ("under_maintenance", "retired"),
    ("missing", "available"),
    ("lost", "available"),
    ("stolen", "available"),
    ("retired", "disposed"),
]

WRITE_ROLES = ["system_admin", "asset_manager", "operator"]

DEPARTMENTS = [
    ("ENG", "Engineering"),
    ("FIN", "Finance"),
    ("HR", "Human Resources"),
    ("OPS", "Operations"),
    ("SALES", "Sales"),
    ("MKT", "Marketing"),
    ("IT", "IT Services"),
    ("LEGAL", "Legal"),
]

LOCATIONS = [
    ("HQ-1", "HQ Building 1", "HQ Campus", "Building 1", "1", "101"),
    ("HQ-2", "HQ Building 2", "HQ Campus", "Building 2", "2", "210"),
    ("HQ-DC", "HQ Data Closet", "HQ Campus", "Building 1", "B1", "B12"),
    ("NYC-01", "New York Office", "New York", "Main", "3", "305"),
    ("NYC-02", "New York Lab", "New York", "Annex", "1", "110"),
    ("LON-01", "London Office", "London", "Main", "4", "402"),
    ("LON-02", "London Store Room", "London", "Main", "G", "G05"),
    ("BER-01", "Berlin Office", "Berlin", "Main", "2", "201"),
    ("SIN-01", "Singapore Office", "Singapore", "Main", "5", "501"),
    ("SYD-01", "Sydney Office", "Sydney", "Main", "1", "115"),
    ("REMOTE", "Remote Worker", "Remote", "", "", ""),
    ("WH-01", "Central Warehouse", "Warehouse Campus", "Warehouse 1", "G", "A1"),
]

COST_CENTERS = [
    ("CC-100", "Engineering Ops"),
    ("CC-200", "Corporate IT"),
    ("CC-300", "Sales Enablement"),
    ("CC-400", "Facilities"),
    ("CC-500", "Executive"),
    ("CC-600", "Customer Support"),
]

SUPPLIERS = [
    ("ACME", "Acme Computers"),
    ("DELL-EMC", "Dell Technologies"),
    ("LENOVO", "Lenovo"),
    ("APPLE", "Apple"),
    ("HP-INC", "HP Inc."),
    ("IKEA-B2B", "IKEA Business"),
    ("STEELCASE", "Steelcase"),
    ("CDW", "CDW"),
]

CATEGORIES = [
    ("LAPTOP", "Laptop", [("ram_gb", "RAM (GB)", "number", True), ("cpu", "CPU", "text", False)]),
    ("DESKTOP", "Desktop", [("ram_gb", "RAM (GB)", "number", False)]),
    ("MONITOR", "Monitor", [("size_in", "Size (inches)", "number", False)]),
    ("PHONE", "Mobile Phone", [("imei", "IMEI", "text", False)]),
    ("FURNITURE", "Furniture", []),
]

DEMO_USERS = [
    ("admin", "system_admin", True),
    ("manager", "asset_manager", False),
    ("deptmgr", "department_manager", False),
    ("operator", "operator", False),
    ("employee", "employee", False),
    ("auditor", "auditor", False),
]


class Command(BaseCommand):
    help = "Seed non-sensitive development data. Idempotent."

    def handle(self, *args, **options) -> None:
        env_password = os.environ.get("SEED_DEMO_PASSWORD")
        password = env_password or secrets.token_urlsafe(12)
        generated = not env_password
        with transaction.atomic():
            statuses = self._seed_statuses()
            conditions = self._seed_conditions()
            self._seed_transitions(statuses)
            departments = self._seed_departments()
            locations = self._seed_locations()
            self._seed_cost_centers()
            suppliers = self._seed_suppliers()
            categories = self._seed_categories()
            users = self._seed_users(password, departments, locations)
            created_assets = self._seed_assets(
                statuses, conditions, departments, locations, suppliers, categories, users
            )
            self._seed_saved_views(users)
        self.stdout.write(self.style.SUCCESS("Development seed data is ready."))
        if generated:
            self.stdout.write(
                f"Generated demo password for all demo users (local dev only): {password}"
            )
        if created_assets:
            self.stdout.write(f"Seeded {created_assets} demo assets.")

    def _seed_statuses(self) -> dict:
        result = {}
        for code, label, icon, treatment, order, terminal in STATUSES:
            status, _ = AssetStatus.objects.get_or_create(
                code=code,
                defaults={
                    "label": label,
                    "icon": icon,
                    "semantic_treatment": treatment,
                    "sort_order": order,
                    "is_terminal": terminal,
                },
            )
            result[code] = status
        return result

    def _seed_conditions(self) -> dict:
        result = {}
        for code, label, icon, treatment, order in CONDITIONS:
            condition, _ = AssetCondition.objects.get_or_create(
                code=code,
                defaults={
                    "label": label,
                    "icon": icon,
                    "semantic_treatment": treatment,
                    "sort_order": order,
                },
            )
            result[code] = condition
        return result

    def _seed_transitions(self, statuses: dict) -> None:
        for from_code, to_code in TRANSITION_PAIRS:
            StatusTransitionRule.objects.get_or_create(
                from_status=statuses[from_code],
                to_status=statuses[to_code],
                defaults={"allowed_roles": WRITE_ROLES},
            )

    def _seed_departments(self) -> list:
        return [
            Department.objects.get_or_create(code=code, defaults={"name": name})[0]
            for code, name in DEPARTMENTS
        ]

    def _seed_locations(self) -> list:
        locations = []
        for code, name, site, building, floor, room in LOCATIONS:
            location, _ = Location.objects.get_or_create(
                code=code,
                defaults={
                    "name": name,
                    "site": site,
                    "building": building,
                    "floor": floor,
                    "room": room,
                },
            )
            locations.append(location)
        return locations

    def _seed_cost_centers(self) -> None:
        for code, name in COST_CENTERS:
            CostCenter.objects.get_or_create(code=code, defaults={"name": name})

    def _seed_suppliers(self) -> list:
        return [
            Supplier.objects.get_or_create(code=code, defaults={"name": name})[0]
            for code, name in SUPPLIERS
        ]

    def _seed_categories(self) -> list:
        categories = []
        for code, name, attributes in CATEGORIES:
            category, _ = Category.objects.get_or_create(code=code, defaults={"name": name})
            for key, label, field_type, required in attributes:
                CategoryAttributeDefinition.objects.get_or_create(
                    category=category,
                    key=key,
                    defaults={
                        "label": label,
                        "field_type": field_type,
                        "required": required,
                    },
                )
            categories.append(category)
        return categories

    def _seed_users(self, password: str, departments: list, locations: list) -> dict:
        user_model = get_user_model()
        users = {}
        for username, role, is_admin in DEMO_USERS:
            user, created = user_model.objects.get_or_create(
                username=username,
                defaults={
                    "role": role,
                    "display_name": username.title(),
                    "is_staff": is_admin,
                    "is_superuser": is_admin,
                    "department": departments[0] if username in {"deptmgr", "employee"} else None,
                },
            )
            if created:
                user.set_password(password)
                user.save(update_fields=["password"])
            users[username] = user
        UserScope.objects.get_or_create(
            user=users["deptmgr"], scope_type="department", department=departments[0]
        )
        UserScope.objects.get_or_create(
            user=users["operator"], scope_type="location", location=locations[0]
        )
        return users

    def _seed_assets(
        self,
        statuses: dict,
        conditions: dict,
        departments: list,
        locations: list,
        suppliers: list,
        categories: list,
        users: dict,
    ) -> int:
        if Asset.objects.exists():
            return 0
        rng = random.Random(20240229)  # deterministic demo dataset
        today = timezone.now().date()
        pool = ["in_stock", "in_stock", "available", "available", "assigned"]
        count = 0
        for index in range(200):
            category = categories[index % len(categories)]
            status = statuses[rng.choice(pool)]
            asset = Asset.objects.create(
                tag=f"AST-{100001 + index:06d}",
                name=f"{category.name} unit {index + 1}",
                category=category,
                status=status,
                condition=rng.choice(list(conditions.values())),
                department=departments[index % len(departments)],
                location=locations[index % len(locations)],
                supplier=suppliers[index % len(suppliers)],
                serial_number=f"SN{200000 + index}",
                manufacturer="Acme",
                model=f"Model-{index % 7}",
                acquisition_type="purchased",
                purchase_date=today - timedelta(days=rng.randint(30, 900)),
                warranty_start=today - timedelta(days=rng.randint(30, 300)),
                warranty_end=today + timedelta(days=rng.randint(-30, 700)),
                category_attributes={"ram_gb": 16} if category.code == "LAPTOP" else {},
                created_by=users["admin"],
                updated_by=users["admin"],
            )
            if status.code == "assigned":
                asset.custodian = users["employee"]
                asset.save(update_fields=["custodian", "updated_at"])
                Assignment.objects.create(
                    asset=asset,
                    custodian=users["employee"],
                    department=asset.department,
                    location=asset.location,
                )
            LifecycleEvent.objects.create(
                asset=asset,
                event_type="registered",
                actor=users["admin"],
                summary=f"Asset {asset.tag} registered (seed).",
            )
            count += 1
        return count

    def _seed_saved_views(self, users: dict) -> None:
        SavedView.objects.get_or_create(
            owner=users["admin"],
            name="All active assets",
            defaults={
                "config": {"filters": {"record_status": "active"}, "ordering": "tag"},
                "shared": True,
            },
        )
