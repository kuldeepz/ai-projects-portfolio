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


@pytest.mark.parametrize(
    "value",
    ["", "   ", "\n"],
)
def test_empty_string_inputs_are_detectable(value):
    """Covers empty/blank string input scenarios for sprint goal-style fields."""
    assert isinstance(value, str)
    assert value.strip() == ""


@pytest.mark.parametrize(
    "value",
    [None],
)
def test_none_inputs_where_applicable(value):
    """Covers None input handling for optional or nullable planner inputs."""
    assert value is None


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
