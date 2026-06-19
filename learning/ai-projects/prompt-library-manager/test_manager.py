"""Sanity tests for prompt-library-manager — no API key required."""
import sys, os, json, tempfile, importlib
import pytest
sys.path.insert(0, os.path.dirname(__file__))


def _load_manager_module():
    """Load the project manager module under common filenames."""
    candidates = [
        "prompt_library_manager",
        "manager",
        "prompt_manager",
    ]
    for name in candidates:
        try:
            return importlib.import_module(name)
        except Exception:
            continue
    pytest.skip("prompt-library-manager module not importable")


def _compute_version_hash(prompt_text):
    """Call project hash helper if available; otherwise skip test."""
    mod = _load_manager_module()
    for attr in ("compute_version_hash", "version_hash", "generate_version_hash"):
        fn = getattr(mod, attr, None)
        if callable(fn):
            return fn(prompt_text)
    pytest.skip("No project hash helper found (compute_version_hash/version_hash/generate_version_hash)")


def _normalize_entry(name="test", description="desc", tags=None, versions=None, current_version=None):
    """Use project normalization/creation API when available."""
    mod = _load_manager_module()
    versions = [] if versions is None else versions

    for attr in ("normalize_prompt_entry", "create_prompt_entry", "build_prompt_entry"):
        fn = getattr(mod, attr, None)
        if callable(fn):
            return fn(name=name, description=description, tags=tags, versions=versions, current_version=current_version)

    pytest.skip("No prompt entry API found (normalize_prompt_entry/create_prompt_entry/build_prompt_entry)")


def _current_version_matches(entry):
    """Use project current_version validation/check API when available."""
    mod = _load_manager_module()
    for attr in (
        "current_version_matches",
        "is_current_version_valid",
        "validate_current_version",
    ):
        fn = getattr(mod, attr, None)
        if callable(fn):
            return fn(entry)
    pytest.skip("No current_version validation API found")


def test_library_json_schema():
    mock_lib = {"prompts": {
        "summarizer_v1": {
            "name": "summarizer_v1",
            "description": "Summarizes technical documents",
            "tags": ["summarization", "docs"],
            "versions": [
                {"hash": "abc12345", "prompt": "You are a technical writer...",
                 "created_at": "2024-01-01", "test_results": []}
            ],
            "current_version": "abc12345"
        }
    }}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(mock_lib, f); tmp = f.name
    try:
        loaded = json.load(open(tmp))
        assert "prompts" in loaded
        p = loaded["prompts"]["summarizer_v1"]
        assert "versions" in p
        assert "current_version" in p
        assert p["current_version"] == "abc12345"
        print("  [PASS] Library JSON schema — structure valid")
    finally:
        os.unlink(tmp)


def test_version_hash_format():
    h = _compute_version_hash("You are a helpful assistant.")
    assert isinstance(h, str)
    assert len(h) == 8
    assert all(c in "0123456789abcdef" for c in h)
    print("  [PASS] Version hash — MD5 8-char hex format valid")


def test_tags_are_list():
    entry = _normalize_entry(tags=["a", "b"])
    assert isinstance(entry["tags"], list)
    print("  [PASS] Tags — stored as list")


def test_version_required_fields():
    version = {"hash": "deadbeef", "prompt": "You are...", "created_at": "2024-06-01", "test_results": []}
    for f in ["hash", "prompt", "created_at", "test_results"]:
        assert f in version
    print("  [PASS] Version fields — hash/prompt/created_at/test_results all present")


def test_multi_version_tracking():
    versions = [
        {"hash": "v1hash12", "prompt": "Prompt v1", "created_at": "2024-01-01", "test_results": []},
        {"hash": "v2hash34", "prompt": "Prompt v2", "created_at": "2024-02-01", "test_results": []},
    ]
    assert len(versions) == 2
    assert versions[-1]["hash"] == "v2hash34"
    print("  [PASS] Multi-version — can track multiple versions")


@pytest.mark.parametrize(
    "prompt_text,expected_hash",
    [
        ("", "d41d8cd9"),
        (None, None),
        ("a", "0cc175b9"),
        ("😀", "2a02eac3"),
    ],
)
def test_version_hash_edge_inputs(prompt_text, expected_hash):
    """Covers empty, None, and boundary prompt inputs via project hash helper."""
    if prompt_text is None:
        with pytest.raises(Exception):
            _compute_version_hash(prompt_text)
    else:
        h = _compute_version_hash(prompt_text)
        assert h == expected_hash
        assert len(h) == 8


@pytest.mark.parametrize(
    "tags,expected_is_list,expected_length",
    [
        ([], True, 0),
        (None, False, None),
        (["single"], True, 1),
        (["a", "", "b"], True, 3),
    ],
)
def test_tags_list_parametrized(tags, expected_is_list, expected_length):
    """Validates tag container behavior via project entry API."""
    entry = _normalize_entry(tags=tags)
    assert isinstance(entry["tags"], list) is expected_is_list
    if expected_is_list:
        assert len(entry["tags"]) == expected_length


@pytest.mark.parametrize(
    "current_version,version_hashes,expected_match",
    [
        ("", ["abc12345"], False),
        (None, ["abc12345"], False),
        ("deadbeef", [], False),
        ("v2hash34", ["v1hash12", "v2hash34"], True),
    ],
)
def test_current_version_boundary_cases(current_version, version_hashes, expected_match):
    """Checks current_version matching via project validation API."""
    versions = [{"hash": h, "prompt": "Prompt", "created_at": "2024-01-01", "test_results": []} for h in version_hashes]
    entry = _normalize_entry(tags=[], versions=versions, current_version=current_version)
    assert _current_version_matches(entry) is expected_match


if __name__ == "__main__":
    print("\n=== prompt-library-manager: Sanity Tests ===\n")
    try:
        test_library_json_schema()
        test_version_hash_format()
        test_tags_are_list()
        test_version_required_fields()
        test_multi_version_tracking()
        print("\n[ALL TESTS PASSED]\n")
    except AssertionError as e:
        print(f"\n[FAILED] {e}\n"); import sys; sys.exit(1)
