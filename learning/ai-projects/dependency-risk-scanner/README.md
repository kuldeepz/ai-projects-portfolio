# Dependency Risk Scanner

AI-powered dependency vulnerability scanner. Analyzes `requirements.txt` or `package.json` and produces a risk report with upgrade commands — no network calls needed for the analysis.

## What It Does

- **5 risk levels** — critical 🔴 · high 🟠 · medium 🟡 · low 🔵 · ok ✅
- **Per-package analysis** — known CVEs, EOL status, yanked releases
- **Upgrade commands** — ready-to-run `pip install` or `npm install` commands
- **Critical action flag** — boolean for CI/CD gate integration
- **Multi-ecosystem** — Python (requirements.txt) and Node.js (package.json)

## Quick Start

```bash
cd dependency-risk-scanner
pip install -r requirements.txt
cp .env.example .env   # add your OPENAI_API_KEY

# Scan a requirements file:
python scanner.py path/to/requirements.txt

# Scan package.json:
python scanner.py path/to/package.json
```

## Sample Output

```
Dependency Risk Report — requirements.txt
==========================================
Ecosystem: python
Total Packages: 12
Critical Action Required: YES

🔴 CRITICAL  flask==1.0.0        CVE-2023-30861 (session cookie exposure) → pip install flask>=2.3.3
🟠 HIGH       pillow==8.0.0       3 CVEs in image processing → pip install pillow>=10.0.1  
🟡 MEDIUM     requests==2.20.0    SSRF risk in older versions → pip install requests>=2.31.0
✅ OK         pytest==7.4.0       No known issues
```

## Run Tests (No API Key Required)

```bash
python test_scanner.py
```

## Tech Stack

- OpenAI GPT-4o-mini with function calling
- No OSV/NVD API calls — LLM knowledge base for risk assessment
