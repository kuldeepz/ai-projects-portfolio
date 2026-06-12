# AI Unit Test Generator

Point it at any Python file and get a complete `pytest` test suite back — covering happy paths, edge cases, boundary values, and error conditions. Uses AST parsing to understand the code structure before generating tests.

## Features

- **Full pytest file generated** — Ready to run, no editing needed
- **AST-based analysis** — Parses function signatures before sending to AI
- **Parametrized tests** — Uses `pytest.mark.parametrize` for multiple cases
- **Edge cases covered** — Empty input, None, boundary values, type errors
- **Mocking** — External dependencies (I/O, network, DB) are mocked
- **Coverage notes** — Explains what's covered and what needs integration tests
- **unittest support** — Optional `--framework unittest` flag
- **Preview in terminal** — Shows first 2000 chars of generated tests

## Setup

```bash
cd unit-test-generator

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# Add your OpenAI API key
```

## Usage

```bash
# Generate pytest tests for a Python module
python generator.py my_module.py

# Use unittest instead of pytest
python generator.py utils.py --framework unittest
```

**Example:** Given `calculator.py`:
```python
def divide(a: float, b: float) -> float:
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b

def is_palindrome(s: str) -> bool:
    s = s.lower().strip()
    return s == s[::-1]
```

**Generated** `test_calculator.py`:
```python
import pytest
from calculator import divide, is_palindrome

class TestDivide:
    def test_divide_positive_numbers(self):
        assert divide(10, 2) == 5.0

    def test_divide_by_zero_raises(self):
        with pytest.raises(ValueError, match="Cannot divide by zero"):
            divide(10, 0)

    @pytest.mark.parametrize("a,b,expected", [
        (10, 2, 5.0), (-6, 3, -2.0), (0, 5, 0.0)
    ])
    def test_divide_parametrized(self, a, b, expected):
        assert divide(a, b) == expected

class TestIsPalindrome:
    def test_palindrome_true(self):
        assert is_palindrome("racecar") is True

    def test_palindrome_case_insensitive(self):
        assert is_palindrome("Racecar") is True

    def test_not_palindrome(self):
        assert is_palindrome("hello") is False

    def test_empty_string(self):
        assert is_palindrome("") is True
```

## Run Tests

```bash
python test_generator.py   # sanity tests (no API key)
pytest test_calculator.py  # run generated tests
```

## Tech Stack

| Component | Technology |
|---|---|
| LLM | OpenAI GPT-4o-mini |
| Code Analysis | Python `ast` module |
| Structured Output | OpenAI Function Calling |
| Terminal UI | Rich |

## Project Structure

```
unit-test-generator/
├── generator.py        # Main application
├── test_generator.py   # Sanity tests for the generator itself
├── requirements.txt
├── .env.example
└── README.md
```

## Notes

- Source files are truncated to 8000 characters — for large modules, run per-file
- Generated tests assume the source module is importable from the same directory
- Always review generated tests before committing — AI may miss project-specific invariants
