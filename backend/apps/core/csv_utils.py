"""CSV export sanitization (formula-injection mitigation; FR-018/FR-019, stack §11).

Pure-Python module (no Django imports) so it can be reused by import/export
services and tested in isolation.
"""

DANGEROUS_PREFIXES = ("=", "+", "-", "@")


def sanitize_csv_value(value: object) -> str:
    """Prefix dangerous leading characters with a single quote so spreadsheet
    applications treat the cell as text."""
    text = "" if value is None else str(value)
    if text.startswith(DANGEROUS_PREFIXES):
        return "'" + text
    return text


def sanitize_csv_row(values: list[object]) -> list[str]:
    return [sanitize_csv_value(value) for value in values]
