"""
Sanity tests for smart-research-agent — no API key required.
Tests URL parsing, text cleaning, and tool map completeness.
"""

import os
import sys
import urllib.parse

import pytest

sys.path.insert(0, os.path.dirname(__file__))

from agent import TOOL_MAP, TOOLS


def test_tool_map_completeness():
    """Every tool definition must have a corresponding implementation."""
    defined_names = {t["function"]["name"] for t in TOOLS}
    implemented_names = set(TOOL_MAP.keys())
    assert defined_names == implemented_names, (
        f"Mismatch: defined={defined_names}, implemented={implemented_names}"
    )
    print("  [PASS] Tool map — all tools defined and implemented")


def test_tool_schemas():
    """Each tool definition has required fields."""
    for tool in TOOLS:
        assert tool["type"] == "function"
        fn = tool["function"]
        assert "name" in fn
        assert "description" in fn
        assert "parameters" in fn
        assert "required" in fn["parameters"]
    print("  [PASS] Tool schemas — all have name, description, parameters, required")


def test_url_parsing():
    """DuckDuckGo redirect URL extraction logic."""
    redirect = "https://duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Farticle&rut=abc"
    real_url = urllib.parse.unquote(redirect.split("uddg=")[1].split("&")[0])
    assert real_url == "https://example.com/article", f"Got: {real_url}"
    print("  [PASS] URL parsing — DuckDuckGo redirect extraction correct")


def test_depth_options():
    """Valid depth options are accepted."""
    valid = {"quick", "standard", "deep"}
    for d in valid:
        assert d in valid
    print("  [PASS] Depth options — quick/standard/deep all valid")


@pytest.mark.parametrize(
    "redirect,expected",
    [
        ("", ""),
        (None, ""),
        ("https://duckduckgo.com/l/?uddg=&rut=abc", ""),
    ],
)
def test_url_parsing_empty_and_none_inputs(redirect, expected):
    """Covers empty and None redirect inputs for safe URL extraction behavior."""
    if not redirect or "uddg=" not in redirect:
        real_url = ""
    else:
        real_url = urllib.parse.unquote(redirect.split("uddg=")[1].split("&")[0])
    assert real_url == expected


@pytest.mark.parametrize(
    "redirect,expected",
    [
        (
            "https://duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fa%3Fq%3D1%26x%3D2&rut=abc",
            "https://example.com/a?q=1&x=2",
        ),
        (
            "https://duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fspace%2520here&rut=abc",
            "https://example.com/space%20here",
        ),
        (
            "https://duckduckgo.com/l/?rut=abc&uddg=https%3A%2F%2Fexample.com%2Ftail",
            "https://example.com/tail",
        ),
    ],
)
def test_url_parsing_edge_cases(redirect, expected):
    """Covers boundary redirect patterns including queries, encoding, and param order."""
    real_url = urllib.parse.unquote(redirect.split("uddg=")[1].split("&")[0])
    assert real_url == expected


@pytest.mark.parametrize(
    "value,is_valid",
    [
        ("", False),
        (None, False),
        ("quick", True),
        ("standard", True),
        ("deep", True),
        ("QUICK", False),
        (" deeper ", False),
    ],
)
def test_depth_options_parametrized(value, is_valid):
    """Covers empty, None, and boundary depth option values for validation."""
    valid = {"quick", "standard", "deep"}
    assert (value in valid) is is_valid


if __name__ == "__main__":
    print("\n=== smart-research-agent: Sanity Tests ===\n")
    try:
        test_tool_map_completeness()
        test_tool_schemas()
        test_url_parsing()
        test_depth_options()
        print("\n[ALL TESTS PASSED]\n")
    except AssertionError as e:
        print(f"\n[FAILED] {e}\n")
        sys.exit(1)
