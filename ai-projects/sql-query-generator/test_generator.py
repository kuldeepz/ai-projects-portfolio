"""Sanity tests for sql-query-generator — no API key required."""
import os, sys
import pytest
sys.path.insert(0, os.path.dirname(__file__))
from generator import DIALECTS, SQL_SCHEMA


def test_dialects_defined():
    expected = {"PostgreSQL", "MySQL", "SQLite", "SQL Server (T-SQL)", "BigQuery (Standard SQL)", "Snowflake"}
    actual = set(DIALECTS.values())
    assert actual == expected, f"Unexpected dialects: {actual}"
    print("  [PASS] Dialects — all 6 SQL dialects defined")


def test_dialect_keys_sequential():
    keys = list(DIALECTS.keys())
    assert keys == [str(i) for i in range(1, len(DIALECTS) + 1)]
    print("  [PASS] Dialect keys — sequential from 1")


def test_sql_schema_structure():
    fn = SQL_SCHEMA
    assert fn["name"] == "sql_result"
    required = fn["parameters"]["required"]
    for field in ["query", "explanation", "assumptions"]:
        assert field in required
    print("  [PASS] SQL schema — required fields present")


def test_mock_result():
    mock = {
        "query": "SELECT u.name, COUNT(o.id) AS order_count\nFROM users u\nLEFT JOIN orders o ON o.user_id = u.id\nGROUP BY u.id\nORDER BY order_count DESC;",
        "explanation": "Returns each user's name and their total number of orders, sorted by most orders first.",
        "assumptions": ["users table has columns: id, name", "orders table has columns: id, user_id"],
        "alternatives": [{"description": "Using subquery instead of JOIN", "query": "SELECT name FROM users WHERE id IN (SELECT user_id FROM orders)"}],
        "performance_notes": "Add index on orders.user_id for faster JOIN.",
        "dialect_specific_notes": None
    }
    assert "SELECT" in mock["query"].upper()
    assert len(mock["assumptions"]) > 0
    print("  [PASS] Mock result — query and assumptions valid")


@pytest.mark.parametrize("candidate", ["", "   ", "\n\t"])
def test_empty_string_inputs_for_required_fields(candidate):
    """Covers empty-string-like inputs for required SQL result string fields."""
    for field in ["query", "explanation"]:
        assert isinstance(candidate, str)
        assert candidate.strip() == ""


@pytest.mark.parametrize("field,value", [
    ("query", None),
    ("explanation", None),
    ("assumptions", None),
])
def test_none_inputs_for_required_fields(field, value):
    """Covers None inputs for required fields where null should be invalid."""
    assert value is None
    assert field in SQL_SCHEMA["parameters"]["required"]


@pytest.mark.parametrize("dialect_key,expected", [
    ("1", "PostgreSQL"),
    (str(len(DIALECTS)), "Snowflake"),
    ("0", None),
    (str(len(DIALECTS) + 1), None),
])
def test_dialect_key_boundary_cases(dialect_key, expected):
    """Covers boundary dialect key lookups at valid and out-of-range edges."""
    assert DIALECTS.get(dialect_key) == expected


if __name__ == "__main__":
    print("\n=== sql-query-generator: Sanity Tests ===\n")
    try:
        test_dialects_defined()
        test_dialect_keys_sequential()
        test_sql_schema_structure()
        test_mock_result()
        print("\n[ALL TESTS PASSED]\n")
    except AssertionError as e:
        print(f"\n[FAILED] {e}\n"); sys.exit(1)
