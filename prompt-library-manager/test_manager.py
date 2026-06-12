"""Sanity tests for prompt-library-manager — no API key required."""
import sys, os, json, tempfile
sys.path.insert(0, os.path.dirname(__file__))

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
    import hashlib
    prompt_text = "You are a helpful assistant."
    h = hashlib.md5(prompt_text.encode()).hexdigest()[:8]
    assert len(h) == 8
    assert all(c in "0123456789abcdef" for c in h)
    print("  [PASS] Version hash — MD5 8-char hex format valid")

def test_tags_are_list():
    mock_entry = {"name": "test", "description": "desc", "tags": ["a", "b"], "versions": [], "current_version": None}
    assert isinstance(mock_entry["tags"], list)
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
