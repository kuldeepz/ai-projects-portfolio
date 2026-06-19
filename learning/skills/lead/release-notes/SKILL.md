---
description: Convert completed work items, commits, or sprint data into polished multi-audience release notes. Use before a release to produce developer changelogs, business summaries, and executive highlights.
---

# Release Notes

Transform a list of completed work items, git log entries, or sprint summary into polished release notes for multiple audiences — developers, business stakeholders, and executives.

## When to Use

- Preparing a product release announcement
- End of sprint — documenting what shipped
- Publishing a changelog for internal or external audiences
- Creating a version history entry for a product wiki

## Steps

1. **Parse the input** — extract work items, commits, or sprint data; identify the release version and date
2. **Categorize items**:
   - `feature` — new user-facing capability
   - `improvement` — enhancement to existing behaviour
   - `bug_fix` — something that was broken, now fixed
   - `security` — vulnerability or hardening fix
   - `breaking_change` — existing callers must change their code
   - `tech_debt` — internal refactor, no user-facing impact
3. **Extract highlights** — top 3 most impactful items for the executive summary
4. **Write 3 versions**:
   - **Technical changelog** — full list, item IDs, technical details for developers
   - **Business summary** — impact-focused, features and fixes in plain English, no IDs
   - **Executive highlights** — 3–5 bullets, pure business value, 1 paragraph max
5. **Flag breaking changes** prominently — they need migration guidance
6. **Save** to `release_notes_vX_Y_Z.md`

## Output Format

```markdown
# Release Notes — v2.4.0
**Released:** YYYY-MM-DD  |  **Type:** Minor

---

## Executive Highlights
- New SSO integration reduces login friction — users no longer need separate passwords
- Critical security patch for session storage — compliance requirement resolved
- API response time improved 40% — faster experience for all users

---

## Business Summary
**New Features**
- Single Sign-On with Azure AD — log in with your company account
- Dark mode — available in user settings

**Improvements**
- Payment processing is now 40% faster
- Email notifications are more reliable with retry logic

**Bug Fixes**
- Fixed: session occasionally expired too early on mobile
- Fixed: order total showed wrong currency symbol in EU regions

---

## Technical Changelog

### New Features
- [US-201] SSO integration with Azure AD via MSAL — see migration guide for config changes
- [US-208] Dark mode: CSS variables, persisted in localStorage

### Improvements
- [PERF-14] Payment service: async processing, removed blocking DB call in hot path
- [PERF-17] Email queue: added exponential backoff and dead-letter queue

### Bug Fixes
- [BUG-45] Session expiry: fixed race condition in token refresh logic
- [BUG-47] Currency: ISO 4217 codes now used throughout, EUR/GBP display corrected

### Security
- [SEC-08] Session tokens now stored in httpOnly cookie, not localStorage

### Breaking Changes
⚠️  [US-201] Auth endpoint moved from `/api/auth` to `/api/v2/auth`.
Clients must update their base URL. See migration guide: docs/migration-v2.4.md
```

## Example Invocation

```
/release-notes
/release-notes v2.4.0 <paste work items or git log>
```

## Notes

- Executive highlights must be in business language — no ticket IDs, no tech stack names
- Breaking changes must always include a migration path or link to one
- If version is not provided, infer from the work items or ask
- Save the output file as `release_notes_vX_Y_Z.md` in the project root or `docs/`
