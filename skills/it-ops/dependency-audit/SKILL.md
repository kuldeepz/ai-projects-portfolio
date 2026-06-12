---
description: Audit a requirements.txt or package.json for dependency risks — CVEs, outdated packages, EOL versions. Use before a release or security review.
---

# Dependency Audit

Scan a dependency file for security risks, outdated packages, and known vulnerabilities. Produce a risk-rated report with upgrade commands.

## When to Use

- Before a production release or deployment
- As part of a security review or compliance check
- When onboarding to a codebase to understand its dependency health
- After a CVE advisory that may affect your stack

## Steps

1. **Read the dependency file** — `requirements.txt`, `package.json`, `Pipfile`, or `pyproject.toml`
2. **Identify the ecosystem** — Python, Node.js, etc.
3. **Rate each package** using known vulnerability knowledge:
   - `critical` — known CVE with active exploits or CVSS ≥9.0
   - `high` — CVE with significant impact (CVSS 7.0–8.9) or package is abandoned
   - `medium` — outdated major version, known issue, or EOL Python/Node runtime
   - `low` — minor version behind, no known CVE but stale
   - `ok` — no known issues at this version
4. **Generate upgrade commands** — `pip install pkg==X.Y.Z` or `npm install pkg@X.Y.Z`
5. **Flag critical action required** — boolean: does this need to be fixed before next deploy?
6. **Summarize** — total packages, breakdown by risk level, top 3 priorities

## Output Format

```
## Dependency Audit — requirements.txt
**Ecosystem:** Python | **Packages:** 14 | **Critical Action Required:** YES

### Risk Summary
🔴 Critical: 1  🟠 High: 2  🟡 Medium: 3  🔵 Low: 4  ✅ OK: 4

### Findings
| Risk     | Package          | Issue                              | Fix Command                        |
|----------|------------------|------------------------------------|------------------------------------|
| 🔴 CRITICAL | flask==1.0.0  | CVE-2023-30861 — session exposure  | pip install flask>=2.3.3           |
| 🟠 HIGH   | pillow==8.0.0   | CVE-2023-44271 — image parse RCE   | pip install pillow>=10.0.1         |
| 🟡 MEDIUM | requests==2.20.0 | SSRF risk in older redirect logic | pip install requests>=2.31.0      |
| ✅ OK     | pytest==7.4.0   | No known issues                    | —                                  |

### Top 3 Priorities
1. Upgrade flask immediately — active exploit in the wild
2. Upgrade pillow before next image-processing deployment
3. Upgrade requests before next external API integration
```

## Example Invocation

```
/dependency-audit
/dependency-audit requirements.txt
/dependency-audit package.json
```

## Notes

- Risk ratings are based on knowledge up to training cutoff — always cross-check against osv.dev or nvd.nist.gov for latest CVEs
- If pinned to an exact version and it's `ok`, still flag if it's >2 major versions behind
- For monorepos with multiple package files, audit each one separately
