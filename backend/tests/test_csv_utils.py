"""Pure-Python tests: runnable in any environment (no Django required)."""

from apps.core.csv_utils import sanitize_csv_row, sanitize_csv_value


def test_formula_prefixes_are_escaped():
    assert sanitize_csv_value("=SUM(A1:A2)") == "'=SUM(A1:A2)"
    assert sanitize_csv_value("+1") == "'+1"
    assert sanitize_csv_value("-10") == "'-10"
    assert sanitize_csv_value("@cmd") == "'@cmd"


def test_normal_values_pass_through():
    assert sanitize_csv_value("AST-000001") == "AST-000001"
    assert sanitize_csv_value("Laptop 15") == "Laptop 15"
    assert sanitize_csv_value(1234) == "1234"


def test_none_becomes_empty_string():
    assert sanitize_csv_value(None) == ""


def test_row_sanitization():
    assert sanitize_csv_row(["ok", "=bad", None]) == ["ok", "'=bad", ""]
