# Job Search Agent

An automated job search agent that scans multiple job boards, scores results against your resume using AI, and emails you a digest of relevant roles.

**Runs every 30 minutes. Zero duplicates. Resume-matched relevance scoring.**

---

## Features

| Feature | Detail |
|---|---|
| **Sources** | Arbeitnow (EU jobs API), LinkedIn (public search), Remotive (remote jobs API) |
| **Filtering** | Your keywords + target locations from `.env` |
| **AI Scoring** | GPT-4o mini rates each job against your resume (0–100%). Below-threshold jobs are silently dropped |
| **Email digest** | HTML email with relevance badges, visa sponsorship flags, salary info |
| **Deduplication** | JSON-based — once a job is processed it is never re-sent |
| **Visa detection** | Regex scan of job text for sponsorship mentions |
| **Scheduling** | Windows Task Scheduler (included helper script) |

---

## Quick Start

### 1. Clone / download

```bash
git clone <repo-url> JobSearchAgent
cd JobSearchAgent
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

Minimum install (no AI scoring, no `.docx` resume):
```bash
pip install requests beautifulsoup4 lxml
```

### 3. Configure

```bash
cp .env.example .env
```

Open `.env` and fill in **at minimum**:

```
SMTP_USER=you@gmail.com
SMTP_APP_PASSWORD=xxxx xxxx xxxx xxxx   # Gmail App Password (see below)
NOTIFY_EMAIL=you@gmail.com
SEARCH_KEYWORDS=engineering manager,AI lead,tech lead
LOCATIONS=Germany: berlin, munich; Netherlands: amsterdam
```

> **Gmail App Password setup:**
> 1. Enable 2-Step Verification on your Google account
> 2. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
> 3. Create an App Password → copy the 16-character code into `.env`

### 4. Add your resume (optional but recommended)

Create a `resume.md` file in the project folder with your resume content (plain text / Markdown).

```
# Jane Smith
Senior Software Engineer — 8 years Python, distributed systems, team lead...
```

Or set `RESUME_PATH` in `.env` to point to an existing `.docx` or `.md` file.

> Without a resume, all keyword-matching jobs are emailed unscored.

### 5. Test it

```bash
python main.py --dry-run
```

This prints matching jobs to the console — no email sent, nothing saved.

### 6. Run for real

```bash
python main.py
```

---

## Scheduling (Windows)

Run once as Administrator to create a Task Scheduler entry:

```bash
python setup_scheduler.py
```

Options:
```bash
python setup_scheduler.py --interval 60        # every 60 minutes
python setup_scheduler.py --task-name MyJobs   # custom task name
python setup_scheduler.py --delete             # remove the task
```

Manual task control:
```bash
schtasks /Run    /TN JobSearchAgent    # trigger now
schtasks /End    /TN JobSearchAgent    # stop running instance
schtasks /Delete /TN JobSearchAgent    # remove task
```

---

## AI Scoring Setup

Without credentials, all keyword-matching jobs are included (no filtering by relevance).

### Option A — Standard OpenAI

1. Get an API key from [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. Add to `.env`:
   ```
   OPENAI_API_KEY=sk-...
   ```

### Option B — Azure OpenAI

```
AZURE_OPENAI_KEY=your-key
AZURE_OPENAI_ENDPOINT=https://YOUR-RESOURCE.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini
```

> Azure takes precedence if both are configured.

---

## Configuration Reference

All settings live in `.env`. See `.env.example` for the full template.

| Variable | Default | Description |
|---|---|---|
| `SMTP_USER` | — | Gmail address used to send emails |
| `SMTP_APP_PASSWORD` | — | Gmail App Password (not your login password) |
| `NOTIFY_EMAIL` | — | Recipient email address |
| `SMTP_HOST` | `smtp.gmail.com` | SMTP server (change for Outlook, etc.) |
| `SMTP_PORT` | `587` | SMTP port |
| `OPENAI_API_KEY` | — | Standard OpenAI key (for scoring) |
| `AZURE_OPENAI_KEY` | — | Azure OpenAI key (alternative) |
| `AZURE_OPENAI_ENDPOINT` | — | Azure OpenAI endpoint URL |
| `AZURE_OPENAI_DEPLOYMENT` | `gpt-4o-mini` | Model deployment name |
| `RESUME_PATH` | `resume.md` | Path to your resume (`.md` or `.docx`) |
| `SEARCH_KEYWORDS` | see `.env.example` | Comma-separated role keywords |
| `LOCATIONS` | DE + NL cities | `Country: city1, city2; Country2: city3` |
| `MIN_SCORE` | `40` | Minimum AI relevance % (0 = send all) |
| `MAX_JOB_AGE_DAYS` | `30` | Ignore jobs older than this |

### LOCATIONS format

```
LOCATIONS=Germany: berlin, munich, frankfurt; Netherlands: amsterdam, rotterdam
```

For remote/worldwide only:
```
LOCATIONS=remote
```

---

## CLI Reference

```bash
python main.py                                   # Normal run
python main.py --dry-run                         # Preview only (no email/save)
python main.py --sources arbeitnow               # Single source
python main.py --sources arbeitnow linkedin      # Multiple sources
python main.py --sources remotive --dry-run      # Combine flags
```

Available sources: `arbeitnow`, `linkedin`, `remotive`

---

## Project Structure

```
JobSearchAgent/
├── main.py               Entry point
├── config.py             Loads settings from .env
├── scorer.py             AI relevance scoring (OpenAI / Azure OpenAI)
├── notifier.py           Builds and sends HTML email
├── storage.py            Tracks seen jobs (deduplication)
├── visa_checker.py       Detects visa sponsorship mentions
├── setup_scheduler.py    Windows Task Scheduler helper
├── scrapers/
│   ├── arbeitnow.py      Arbeitnow.com API (EU jobs)
│   ├── linkedin.py       LinkedIn public search scraper
│   └── remotive.py       Remotive.com API (remote jobs)
├── requirements.txt
├── .env.example          Config template — copy to .env
├── .gitignore
└── resume.md             Your resume (create this — not tracked by git)
```

---

## How It Works

```
Every 30 min (Task Scheduler)
      │
      ▼
  Fetch jobs from Arbeitnow + LinkedIn + Remotive
      │
      ▼
  Filter: keyword match + location match
      │
      ▼
  Dedup: remove jobs already seen (seen_jobs.json)
      │
      ▼
  Score: GPT-4o mini rates each job vs. your resume (0–100%)
      │
      ▼
  Filter: drop jobs below MIN_SCORE
      │
      ▼
  Email: HTML digest with badges → NOTIFY_EMAIL
      │
      ▼
  Save: mark all processed jobs as seen
```

---

## Troubleshooting

**No jobs found:**
- Run `--dry-run` and check the console output per source
- Widen your `SEARCH_KEYWORDS` or `LOCATIONS`
- Arbeitnow only covers Europe; use Remotive for worldwide remote roles

**Email not sent:**
- Ensure `SMTP_APP_PASSWORD` is set (not your Google login password)
- Check Gmail 2-Step Verification is enabled
- Try running with `--dry-run` first to isolate scraping vs. email issues

**Scoring not working:**
- Confirm `OPENAI_API_KEY` or Azure credentials are set in `.env`
- Install the openai package: `pip install openai`
- If `resume.md` is missing, scoring is skipped and all jobs are sent

**Windows Task Scheduler fails:**
- Run `python setup_scheduler.py` as Administrator
- Check log at `job_agent.log` in the project folder

---

## Privacy

- `.env` is excluded from git — your credentials are never committed
- Your resume is only sent to OpenAI/Azure OpenAI for scoring; it is not stored externally
- `seen_jobs.json` is local — it just tracks job IDs (no personal data)

---

## License

MIT
