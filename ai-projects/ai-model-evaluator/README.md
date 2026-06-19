# AI Model Evaluator

LLM-as-judge evaluation framework. Run a test suite against any OpenAI model and get per-case scores with hallucination detection, correctness ratings, and an aggregated performance report.

## What It Does

- **LLM-as-judge** — GPT evaluates GPT output against expected answers
- **Per-case scoring** — 0–100 score + correct/partial/incorrect label
- **Hallucination detection** — boolean flag per response
- **Reasoning** — judge explains its scoring decision
- **Suite reports** — pass rate, avg score, hallucination rate, failure patterns

## Quick Start

```bash
cd ai-model-evaluator
pip install -r requirements.txt
cp .env.example .env   # add your OPENAI_API_KEY
python evaluator.py
```

## Sample Output

```
Model Evaluation Report — gpt-4o-mini
======================================
Test Suite: General Reasoning (5 cases)

  TC-001 [correct]   Score: 94   Hallucination: No
    "Capital of France" → "Paris" ✓

  TC-002 [partial]   Score: 61   Hallucination: No
    "Explain SOLID" → Missing DIP explanation

  TC-003 [incorrect] Score: 12   Hallucination: YES ⚠️
    "GPT-4 release date" → Model stated wrong year

Summary:
  Pass Rate: 60%  (3/5 correct or partial)
  Avg Score: 72.4
  Hallucination Rate: 20% (1/5 cases)
  Recommendation: Add grounding for factual date queries
```

## Run Tests (No API Key Required)

```bash
python test_evaluator.py
```

## Tech Stack

- OpenAI GPT-4o-mini (evaluator model + judge model)
- LLM-as-judge pattern — no ground truth labels needed
- Structured output for deterministic scoring
