---
description: Generate comprehensive unit tests for a function, class, or module. Use when you want pytest-style tests covering happy paths, edge cases, and error conditions.
---

# Write Tests

Generate a complete test suite for the target code — no mocks where unnecessary, real assertions, parametrize where it saves repetition.

## When to Use

- A function or class has no tests yet
- You want to increase test coverage before a refactor
- Code was just written and needs a test file created alongside it

## Steps

1. **Read the target code** — understand inputs, outputs, side effects, and dependencies
2. **Identify test cases**:
   - Happy path (normal, expected input)
   - Edge cases (empty, zero, boundary values, max length)
   - Error/exception cases (invalid types, missing required values)
   - State-dependent cases (if the code mutates state or has side effects)
3. **Decide on mocking** — only mock external I/O (network, disk, time); never mock the thing under test
4. **Write the test file** — use `pytest`, `@pytest.mark.parametrize` for repeated patterns, descriptive test names
5. **Add a brief docstring** to each test explaining the scenario, not what the assertion checks

## Output Format

```python
# test_<module>.py
import pytest
from <module> import <function>

class Test<FunctionName>:
    def test_returns_expected_value_for_valid_input(self):
        ...

    def test_raises_value_error_for_empty_string(self):
        with pytest.raises(ValueError):
            ...

    @pytest.mark.parametrize("input,expected", [
        ("case1", result1),
        ("case2", result2),
    ])
    def test_handles_multiple_formats(self, input, expected):
        ...
```

## Example Invocation

```
/write-tests
/write-tests src/utils/parser.py
```

## Notes

- Name tests as `test_<what it does>_<condition>` — readable without reading the body
- Prefer `assert` with a message over bare `assert` for non-obvious checks
- If the code uses a database or external API, mock at the boundary (not inside the unit)
- Output the full file, not just snippets
