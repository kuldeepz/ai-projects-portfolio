# AI Projects Portfolio

Portfolio with production projects and a separate learning archive.

## Repository Structure

```
ai-projects-portfolio/
├── projects/
│   └── job-search-agent/        # active project
└── learning/
    ├── ai-projects/             # learning/demo AI projects
    ├── skills/                  # SKILL.md skill packs
    └── source-to-skill/         # source-to-skill experiments
```

## Active Project

- [projects/job-search-agent/](./projects/job-search-agent/) - Automated job search workflow with scraping, scoring, storage, and notifications.

## Learning Archive

- [learning/ai-projects/](./learning/ai-projects/) - 25 AI/ML project examples.
- [learning/skills/](./learning/skills/) - Skill packs organized by domain.
- [learning/source-to-skill/](./learning/source-to-skill/) - Distillation experiments and generated outputs.

## Quick Start

```bash
git clone https://github.com/kuldeepz/ai-projects-portfolio
cd ai-projects-portfolio/projects/job-search-agent
pip install -r requirements.txt
cp .env.example .env   # add required keys
python main.py
```

## Tech Stack

- LLM: OpenAI GPT-4o-mini (function calling + structured outputs)
- Language: Python 3.10+
- Patterns: Agent loops, scoring pipelines, and automation workflows
