"""Custom serializer fields shared across asset endpoints."""

import re
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ObjectDoesNotExist
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

CURRENCY_RE = re.compile(r"^[A-Z]{3}$")
MAX_MONEY = Decimal("999999999999.99")

_UUID_SCHEMA = {"type": "string", "format": "uuid"}
_RELATED_READ_SCHEMA = {
    "type": "object",
    "properties": {"uuid": _UUID_SCHEMA},
    "required": ["uuid"],
    "additionalProperties": True,
}


@extend_schema_field({"oneOf": [_UUID_SCHEMA, _RELATED_READ_SCHEMA]})
class UUIDRelatedField(serializers.PrimaryKeyRelatedField):
    """Write: related object referenced by its public UUID string.
    Read: compact object {"uuid": ..., <repr_fields>}.

    DRF's pk-only optimization would hand ``to_representation`` a
    ``PKOnlyObject`` (pk only); we need the full instance for the compact
    representation, so the optimization is disabled.
    """

    def __init__(self, **kwargs) -> None:
        self.repr_fields = kwargs.pop("repr_fields", ())
        super().__init__(**kwargs)

    def use_pk_only_optimization(self) -> bool:
        return False

    def to_internal_value(self, data):
        queryset = self.get_queryset()
        try:
            return queryset.get(uuid=data)
        except (ObjectDoesNotExist, TypeError, ValueError):
            self.fail("does_not_exist", pk_value=data)

    def to_representation(self, value) -> dict:
        representation: dict[str, object] = {"uuid": str(value.uuid)}
        for field_name in self.repr_fields:
            representation[field_name] = getattr(value, field_name, None)
        return representation


@extend_schema_field(
    {
        "type": "object",
        "properties": {
            "amount": {"type": "string", "pattern": r"^-?\d+(\.\d{1,2})?$"},
            "currency": {"type": "string", "pattern": r"^[A-Z]{3}$"},
        },
        "required": ["amount", "currency"],
        "nullable": True,
    }
)
class MoneyField(serializers.Field):
    """Money object {"amount": "1234.56", "currency": "USD"} (design D-06).

    Maps onto a model ``<amount_attr>`` / ``<currency_attr>`` pair
    (defaults: ``purchase_price`` / ``purchase_currency``).
    """

    default_error_messages = {
        "invalid": 'Expected an object like {"amount": "1234.56", "currency": "USD"}.'
    }

    def __init__(self, **kwargs) -> None:
        self.amount_attr = kwargs.pop("amount_attr", "purchase_price")
        self.currency_attr = kwargs.pop("currency_attr", "purchase_currency")
        kwargs["source"] = "*"
        super().__init__(**kwargs)

    def to_representation(self, instance) -> dict | None:
        amount = getattr(instance, self.amount_attr, None)
        if amount is None:
            return None
        currency = getattr(instance, self.currency_attr, "") or "USD"
        return {"amount": f"{Decimal(amount):.2f}", "currency": currency}

    def to_internal_value(self, data) -> dict:
        if not isinstance(data, dict):
            self.fail("invalid")
        raw_amount = data.get("amount")
        currency = data.get("currency", "USD")
        try:
            parsed = Decimal(str(raw_amount))
        except (InvalidOperation, TypeError, ValueError):
            self.fail("invalid")
        if parsed.is_nan() or parsed.is_infinite() or abs(parsed) > MAX_MONEY:
            self.fail("invalid")
        exponent = parsed.as_tuple().exponent
        if isinstance(exponent, int) and -exponent > 2:
            self.fail("invalid")
        if not isinstance(currency, str) or not CURRENCY_RE.match(currency):
            self.fail("invalid")
        return {
            self.amount_attr: parsed.quantize(Decimal("0.01")),
            self.currency_attr: currency,
        }
