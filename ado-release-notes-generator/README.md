# ADO Release Notes Generator

Transforms completed Azure DevOps work items into polished, multi-audience release notes — from developer changelogs to executive summaries.

## What It Does

- **Multi-audience** — technical, business, and executive formats
- **Auto-categorization** — features, bug fixes, improvements, breaking changes
- **Markdown output** — saved to `release_notes_vX_Y_Z.md`
- **Highlights extraction** — top 3 headline changes for exec summary

## Quick Start

```bash
cd ado-release-notes-generator
pip install -r requirements.txt
cp .env.example .env   # add your OPENAI_API_KEY
python release_notes.py
```

## Sample Output

```markdown
# Release Notes — v2.4.0

## Highlights
- New SSO integration reduces login friction by 60%
- Critical security patch for session token storage
- Performance: API response time improved 40%

## New Features
- [US-201] Single Sign-On with Azure AD
- [US-208] Dark mode support

## Bug Fixes  
- [BUG-45] Fixed session expiry not refreshing correctly
- [BUG-47] Resolved race condition in payment processing
```

## Run Tests (No API Key Required)

```bash
python test_release_notes.py
```

## Tech Stack

- OpenAI GPT-4o-mini with function calling
- Semver-aware output filenames
- Saves markdown to `release_notes_vX_Y_Z.md`
