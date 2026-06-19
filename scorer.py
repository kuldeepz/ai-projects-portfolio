"""
Resume-based job relevance scorer.
Supports both standard OpenAI and Azure OpenAI.
Jobs below MIN_SCORE are filtered out before emailing.
"""

import json
from pathlib import Path
from config import MIN_SCORE, RESUME_PATH, OPENAI_API_KEY, AZURE_OPENAI_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT

_resume_text = None


def _load_resume() -> str:
    global _resume_text
    if _resume_text is not None:
        return _resume_text

    path = Path(RESUME_PATH)
    try:
        if path.suffix.lower() == ".md" or path.suffix.lower() == ".txt":
            _resume_text = path.read_text(encoding="utf-8")
            print(f"[Scorer] Resume loaded from {path.name} ({len(_resume_text)} chars)")
        elif path.suffix.lower() == ".docx":
            from docx import Document
            doc = Document(str(path))
            _resume_text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
            print(f"[Scorer] Resume loaded from {path.name} ({len(_resume_text)} chars)")
        else:
            print(f"[Scorer] Unsupported resume format: {path.suffix} — skipping scoring")
            _resume_text = ""
    except FileNotFoundError:
        print(f"[Scorer] Resume not found at {path} — skipping scoring")
        _resume_text = ""
    except Exception as e:
        print(f"[Scorer] Failed to read resume: {e}")
        _resume_text = ""

    return _resume_text


def _get_client():
    """Returns (client, deployment) for whichever provider is configured."""
    try:
        from openai import AzureOpenAI, OpenAI
    except ImportError:
        print("[Scorer] openai package not installed. Run: pip install openai")
        return None, None

    if AZURE_OPENAI_KEY and AZURE_OPENAI_ENDPOINT:
        client = AzureOpenAI(
            api_key=AZURE_OPENAI_KEY,
            api_version="2024-02-01",
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
        )
        return client, AZURE_OPENAI_DEPLOYMENT

    if OPENAI_API_KEY:
        client = OpenAI(api_key=OPENAI_API_KEY)
        return client, "gpt-4o-mini"

    return None, None


def score_jobs(jobs: list) -> list:
    """
    Score each job for relevance against the resume.
    Returns jobs with a 'score' field (0–100), filtered to >= MIN_SCORE.
    Falls back to passing all jobs through (score=None) if scoring is unavailable.
    """
    client, deployment = _get_client()
    if client is None:
        print("[Scorer] No OpenAI credentials set — skipping scoring, sending all jobs")
        for j in jobs:
            j["score"] = None
        return jobs

    resume_text = _load_resume()
    if not resume_text:
        print("[Scorer] Resume empty — skipping scoring, sending all jobs")
        for j in jobs:
            j["score"] = None
        return jobs

    resume_snippet = resume_text[:3000]
    scored = []

    for j in jobs:
        job_text = f"Title: {j['title']}\nCompany: {j['company']}\nLocation: {j['location']}\n"
        if j.get("description_snippet"):
            job_text += f"Description: {j['description_snippet']}"

        prompt = (
            "You are a career advisor. Given the candidate's resume and a job posting, "
            "rate how well the candidate matches the job on a scale of 0-100.\n\n"
            f"RESUME (excerpt):\n{resume_snippet}\n\n"
            f"JOB POSTING:\n{job_text}\n\n"
            'Respond with ONLY a JSON object: {"score": <0-100>, "reason": "<one sentence>"}'
        )

        try:
            response = client.chat.completions.create(
                model=deployment,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100,
                temperature=0,
            )
            raw = response.choices[0].message.content.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1].lstrip("json").strip()
            data = json.loads(raw)
            score = int(data.get("score", 0))
            j["score"] = score
            j["score_reason"] = data.get("reason", "")
            safe = j["title"].encode("ascii", "replace").decode("ascii")
            print(f"[Scorer] {score:3d}% — {safe} @ {j['company']}")
        except Exception as e:
            safe = j["title"].encode("ascii", "replace").decode("ascii")
            print(f"[Scorer] Failed to score '{safe}': {e}")
            j["score"] = None

        if j.get("score") is None or j["score"] >= MIN_SCORE:
            scored.append(j)

    filtered = len(jobs) - len(scored)
    if filtered:
        print(f"[Scorer] Filtered out {filtered} jobs below {MIN_SCORE}% match")
    print(f"[Scorer] {len(scored)} jobs passed relevance threshold")
    return scored
