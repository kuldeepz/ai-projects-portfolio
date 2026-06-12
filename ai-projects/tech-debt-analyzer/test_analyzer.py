"""Sanity tests for tech-debt-analyzer — no API key required."""
import sys, os, textwrap, tempfile
sys.path.insert(0, os.path.dirname(__file__))
from analyzer import SCHEMA, collect_code

def test_schema():
    required = SCHEMA["parameters"]["required"]
    for f in ["overall_debt_score", "debt_items", "total_effort_days", "quick_wins", "summary"]:
        assert f in required
    print("  [PASS] Schema — required fields present")

def test_category_enum():
    valid = {"code_quality", "architecture", "security", "testing", "documentation", "dependencies", "performance"}
    actual = set(SCHEMA["parameters"]["properties"]["debt_items"]["items"]["properties"]["category"]["enum"])
    assert actual == valid
    print("  [PASS] Category enum — all 7 debt categories defined")

def test_collect_code_file(tmp_path):
    code = "def hello():\n    print('world')\n"
    p = tmp_path / "sample.py"
    p.write_text(code)
    result = collect_code(str(p))
    assert "hello" in result
    print("  [PASS] Collect code — reads single file correctly")

def test_collect_code_truncation(tmp_path):
    big_code = "x = 1\n" * 10000
    p = tmp_path / "big.py"
    p.write_text(big_code)
    result = collect_code(str(p), max_chars=100)
    assert len(result) <= 100
    print("  [PASS] Collect code — truncates to max_chars limit")

if __name__ == "__main__":
    import pathlib
    print("\n=== tech-debt-analyzer: Sanity Tests ===\n")
    try:
        tmp = pathlib.Path(tempfile.mkdtemp())
        test_schema(); test_category_enum()
        test_collect_code_file(tmp); test_collect_code_truncation(tmp)
        print("\n[ALL TESTS PASSED]\n")
    except AssertionError as e:
        print(f"\n[FAILED] {e}\n"); sys.exit(1)
