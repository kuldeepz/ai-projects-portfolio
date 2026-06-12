"""Sanity tests for ado-sprint-planner — no API key required."""
import sys, os
import pytest

sys.path.insert(0, os.path.dirname(__file__))
from sprint_planner import SCHEMA, SAMPLE_BACKLOG, is_capacity_valid

def test_schema():
    required = SCHEMA["parameters"]["required"]
    for f in ["sprint_goal", "recommended_items", "deferred_items", "total_points", "capacity_utilization_pct", "risks"]:
        assert f in required
    print("  [PASS] Schema — required fields present")

def test_sample_backlog_integrity():
    assert is_capacity_valid(
        SAMPLE_BACKLOG["team"]["velocity"],
        SAMPLE_BACKLOG["team"]["capacity_this_sprint"],
    )
    total_available = sum(i["story_points"] for i in SAMPLE_BACKLOG["items"])
    assert total_available > SAMPLE_BACKLOG["team"]["capacity_this_sprint"], "Backlog should exceed capacity"
    print("  [PASS] Sample backlog — more items than capacity (requires selection logic)")

def test_dependency_present():
    ids = {i["id"] for i in SAMPLE_BACKLOG["items"]}
    for item in SAMPLE_BACKLOG["items"]:
        for dep in item.get("dependencies", []):
            assert dep in ids, f"Dependency {dep} not found in backlog"
    print("  [PASS] Dependencies — all referenced IDs exist in backlog")


@pytest.mark.parametrize("value", ["", "   ", "\n"])
def test_schema_disallows_blank_for_required_string_fields(value):
    """Schema-level check: required string-like outputs should not accept blank values."""
    properties = SCHEMA["parameters"]["properties"]
    required = set(SCHEMA["parameters"].get("required", []))

    for field in required:
        field_schema = properties.get(field, {})
        field_type = field_schema.get("type")
        if field_type == "string":
            min_len = field_schema.get("minLength", 0)
            assert min_len >= 1, f"Required string field '{field}' should enforce non-blank values"


@pytest.mark.parametrize("field", ["sprint_goal", "recommended_items", "deferred_items", "total_points", "capacity_utilization_pct", "risks"])
def test_schema_required_fields_are_not_nullable(field):
    """Schema-level check: required output fields should not be nullable by type."""
    field_schema = SCHEMA["parameters"]["properties"].get(field, {})
    field_type = field_schema.get("type")

    if isinstance(field_type, list):
        assert "null" not in field_type, f"Required field '{field}' should not allow null"
    else:
        assert field_type != "null", f"Required field '{field}' should not be null type"


@pytest.mark.parametrize(
    "velocity,capacity,expected",
    [
        (0, 0, True),
        (10, 12, True),
        (10, 13, False),
        (1, 2, False),
    ],
)
def test_capacity_boundary_cases(velocity, capacity, expected):
    """Covers edge boundaries for capacity relative to 120% of velocity."""
    assert is_capacity_valid(velocity, capacity) is expected


if __name__ == "__main__":
    sys.exit(pytest.main([__file__]))
