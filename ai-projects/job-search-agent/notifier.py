"""Sends an HTML email digest of new matching jobs."""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from config import NOTIFY_EMAIL, SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_APP_PASSWORD, SEARCH_KEYWORDS, ALL_LOCATIONS


def _build_html(jobs: list) -> str:
    rows = ""
    for j in jobs:
        remote_badge = '<span style="color:#16a34a;font-weight:bold">[REMOTE] </span>' if j.get("remote") else ""
        salary_line = f'<br><small style="color:#6b7280">&#128176; {j["salary"]}</small>' if j.get("salary") else ""
        snippet_line = f'<br><small style="color:#374151">{j["description_snippet"]}…</small>' if j.get("description_snippet") else ""

        score = j.get("score")
        if score is not None:
            if score >= 75:
                sc, sb = "#15803d", "#dcfce7"
            elif score >= 55:
                sc, sb = "#b45309", "#fef9c3"
            else:
                sc, sb = "#b91c1c", "#fee2e2"
            score_badge = (
                f'<span style="background:{sb};color:{sc};padding:3px 8px;'
                f'border-radius:12px;font-size:13px;font-weight:bold">{score}% match</span>'
            )
        else:
            score_badge = ""

        visa_badge = (
            '<span style="background:#c7d2fe;color:#3730a3;padding:3px 8px;'
            'border-radius:12px;font-size:13px;font-weight:bold">&#10003; Visa Sponsor</span>'
            if j.get("visa_sponsor") else
            '<span style="background:#d1d5db;color:#374151;padding:3px 8px;'
            'border-radius:12px;font-size:13px;font-weight:bold">No Visa</span>'
        )

        badges = f"{score_badge}&nbsp;{visa_badge}" if score_badge else visa_badge

        rows += f"""
        <tr style="border-bottom:1px solid #e5e7eb">
          <td style="padding:12px 8px">
            <a href="{j['url']}" style="font-size:15px;font-weight:600;color:#1d4ed8;text-decoration:none">
              {remote_badge}{j['title']}
            </a><br>
            <span style="color:#374151">{j['company']}</span> &nbsp;|&nbsp;
            <span style="color:#6b7280">{j['location']}</span>
            {salary_line}{snippet_line}
          </td>
          <td style="padding:12px 8px;text-align:center;white-space:nowrap">
            <span style="background:#dbeafe;color:#1e40af;padding:2px 8px;border-radius:4px;font-size:12px">
              {j['source']}
            </span>
          </td>
          <td style="padding:12px 8px;text-align:center">{badges}</td>
          <td style="padding:12px 8px;text-align:center">
            <a href="{j['url']}" style="background:#1d4ed8;color:white;padding:6px 14px;border-radius:6px;text-decoration:none;font-size:13px">
              View
            </a>
          </td>
        </tr>"""

    kw_display = " / ".join(SEARCH_KEYWORDS[:4])
    loc_display = ", ".join(ALL_LOCATIONS[:5])

    return f"""
    <html><body style="font-family:Arial,sans-serif;max-width:800px;margin:0 auto;padding:20px">
      <h2 style="color:#111827">&#128640; {len(jobs)} New Job{'s' if len(jobs)>1 else ''} Found &mdash; {datetime.now().strftime('%d %b %Y, %H:%M')}</h2>
      <p style="color:#6b7280">Keywords: {kw_display} &nbsp;|&nbsp; Locations: {loc_display}</p>
      <table style="width:100%;border-collapse:collapse;margin-top:16px">
        <thead>
          <tr style="background:#f3f4f6">
            <th style="padding:10px 8px;text-align:left;color:#374151">Role</th>
            <th style="padding:10px 8px;color:#374151">Source</th>
            <th style="padding:10px 8px;color:#374151">Match &amp; Visa</th>
            <th style="padding:10px 8px;color:#374151">Link</th>
          </tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>
      <p style="margin-top:24px;color:#9ca3af;font-size:12px">
        Sent by Job Search Agent &middot; <a href="https://github.com" style="color:#9ca3af">GitHub</a>
      </p>
    </body></html>
    """


def send_notification(jobs: list):
    if not jobs:
        return

    if not SMTP_APP_PASSWORD:
        print("[Notifier] SMTP_APP_PASSWORD not set — printing to console instead:")
        for j in jobs:
            score_str = f" [{j['score']}%]" if j.get("score") is not None else ""
            print(f"  [{j['source']}]{score_str} {j['title']} @ {j['company']} ({j['location']}) → {j['url']}")
        return

    kw_short = " / ".join(k.title() for k in SEARCH_KEYWORDS[:3])
    subject = f"[Jobs] {len(jobs)} new match{'es' if len(jobs)>1 else ''} — {kw_short}"

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = SMTP_USER
        msg["To"] = NOTIFY_EMAIL
        msg["X-Priority"] = "1"
        msg["X-MSMail-Priority"] = "High"
        msg["Importance"] = "High"
        msg.attach(MIMEText(_build_html(jobs), "html"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_APP_PASSWORD)
            server.sendmail(SMTP_USER, NOTIFY_EMAIL, msg.as_string())

        print(f"[Notifier] Email sent to {NOTIFY_EMAIL} with {len(jobs)} jobs")
    except Exception as e:
        print(f"[Notifier] Failed to send email: {e}")
