"""Sanity tests for unit-test-generator — no API key required."""
import os, sys, textwrap
import pytest
sys.path.insert(0, os.path.dirname(__file__))
from generator import extract_function_signatures, TEST_SCHEMA


def test_signature_extraction_functions():
    source = textwrap.dedent("""
        def add(a, b):
            return a + b

        def greet(name, greeting=\"Hello\"):
            return f\"{greeting}, {name}\"

        async def fetch_data(url):
            pass
    """)
    sigs = extract_function_signatures(source)
    assert any("add" in s for s in sigs)
    assert any("greet" in s for s in sigs)
    assert any("fetch_data" in s for s in sigs)
    print("  [PASS] Signature extraction — functions detected (sync and async)")


def test_signature_extraction_class():
    source = textwrap.dedent("""
        class Calculator:
            def multiply(self, x, y):
                return x * y
    """)
    sigs = extract_function_signatures(source)
    assert any("Calculator" in s for s in sigs)
    assert any("multiply" in s for s in sigs)
    print("  [PASS] Signature extraction — class and method detected")


def test_signature_extraction_invalid():
    sigs = extract_function_signatures("this is not python!!!! @@@")
    assert sigs == []
    print("  [PASS] Signature extraction — returns [] for invalid syntax")


def test_schema_structure():
    assert TEST_SCHEMA["name"] == "test_output"
    required = TEST_SCHEMA["parameters"]["required"]
    for field in ["test_file_content", "functions_covered", "test_count", "coverage_notes"]:
        assert field in required
    print("  [PASS] Schema — required fields present")


@pytest.mark.parametrize("source, expected", [
    ("", []),
    ("   \n\t  ", []),
    (textwrap.dedent("""
        # comments only
        # still no functions
    """), []),
])
def test_signature_extraction_empty_inputs(source, expected):
    """Covers empty-string-like inputs and expects no signatures."""
    assert extract_function_signatures(source) == expected


@pytest.mark.parametrize("source", [
    None,
])
def test_signature_extraction_none_input(source):
    """Covers None input handling for signature extraction."""
    with pytest.raises(TypeError):
        extract_function_signatures(source)


@pytest.mark.parametrize("source, expected_names", [
    ("def f(a, /, b, *, c=1):\n    return a + b + c\n", ["f"]),
    ("def ünicode_名(x):\n    return x\n", ["ünicode_名"]),
    ("@decorator\ndef decorated(x):\n    return x\n", ["decorated"]),
])
def test_signature_extraction_edge_cases(source, expected_names):
    """Covers parser edge cases like positional-only args, unicode, and decorators."""
    sigs = extract_function_signatures(source)
    extracted_names = [
        s.split("(")[0].replace("async ", "").replace("def ", "").strip()
        for s in sigs
        if "(" in s
    ]
    assert set(expected_names).issubset(set(extracted_names))


if __name__ == "__main__":
    print("\n=== unit-test-generator: Sanity Tests ===\n")
    try:
        test_signature_extraction_functions()
        test_signature_extraction_class()
        test_signature_extraction_invalid()
        test_schema_structure()
        print("\n[ALL TESTS PASSED]\n")
    except AssertionError as e:
        print(f"\n[FAILED] {e}\n"); sys.exit(1)
