"""Weekly trend-digest email delivery for Beacon AI.

Lets a user subscribe their email to receive the current run's final-analysis PDF once
immediately, then again roughly every 7 days for as long as this app process keeps running.
There's no persistent job queue or OS-level cron here -- this is a single-user local tool (see
the project README's "Feasibility and Responsible AI" section) -- so the "cron job" is a
lightweight in-process daemon thread with subscription state persisted to disk, not a
production scheduler. Restarting the app doesn't lose subscriptions (they're read back from
disk), but it does lose an in-flight countdown; the next check after restart just resumes from
each subscription's last-sent timestamp.
"""

from __future__ import annotations

import json
import os
import re
import smtplib
import threading
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
SUBSCRIPTIONS_PATH = ROOT_DIR / "raw" / "digest_subscriptions.json"
WEEK_SECONDS = 7 * 24 * 60 * 60
_POLL_SECONDS = 60 * 60  # how often the background thread checks for a due subscription

# Standard-ish email shape: at least one char before the @, at least one char in the domain
# label before the dot, and at least one char in the final label after the dot.
_EMAIL_RE = re.compile(
    r"^[A-Za-z0-9](?:[A-Za-z0-9._%+-]*[A-Za-z0-9])?"
    r"@[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?"
    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?)+$"
)


def is_valid_email(email: str) -> bool:
    return bool(_EMAIL_RE.match((email or "").strip()))


def _load_env_file() -> None:
    for candidate in (Path(__file__).with_name(".env"), ROOT_DIR / ".env"):
        if not candidate.exists():
            continue
        for raw_line in candidate.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if key and key not in os.environ:
                os.environ[key] = value.strip().strip('"').strip("'")


_load_env_file()


def _smtp_config() -> dict[str, str] | None:
    host = os.getenv("SMTP_HOST", "").strip()
    if not host:
        return None
    username = os.getenv("SMTP_USERNAME", "").strip()
    return {
        "host": host,
        "port": os.getenv("SMTP_PORT", "587").strip() or "587",
        "username": username,
        "password": os.getenv("SMTP_PASSWORD", "").strip(),
        "from_email": os.getenv("SMTP_FROM_EMAIL", "").strip() or username,
    }


def send_digest_email(to_email: str, pdf_bytes: bytes, pdf_filename: str, subject: str, body: str) -> tuple[bool, str]:
    """Best-effort send; never raises. Returns (success, plain-language status message)."""
    from email.message import EmailMessage

    config = _smtp_config()
    if not config:
        return False, (
            "Email delivery isn't configured yet. Add SMTP_HOST, SMTP_PORT, SMTP_USERNAME, "
            "SMTP_PASSWORD, and SMTP_FROM_EMAIL to .env."
        )
    if not pdf_bytes:
        return False, "No report PDF is available yet to send."

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = config["from_email"] or "beacon-ai@localhost"
    message["To"] = to_email
    message.set_content(body)
    message.add_attachment(pdf_bytes, maintype="application", subtype="pdf", filename=pdf_filename)

    try:
        with smtplib.SMTP(config["host"], int(config["port"]), timeout=20) as server:
            server.starttls()
            if config["username"]:
                server.login(config["username"], config["password"])
            server.send_message(message)
        return True, f"Sent to {to_email}."
    except Exception as exc:  # noqa: BLE001
        return False, f"Couldn't send the digest email: {exc}"


def _read_subscriptions() -> list[dict]:
    if not SUBSCRIPTIONS_PATH.exists():
        return []
    try:
        return json.loads(SUBSCRIPTIONS_PATH.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return []


def _write_subscriptions(rows: list[dict]) -> None:
    SUBSCRIPTIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUBSCRIPTIONS_PATH.write_text(json.dumps(rows, indent=2), encoding="utf-8")


def register_weekly_subscription(email: str, pdf_path: str, company: str) -> None:
    rows = [row for row in _read_subscriptions() if row.get("email", "").lower() != email.strip().lower()]
    now = time.time()
    rows.append(
        {
            "email": email.strip(),
            "pdf_path": pdf_path,
            "company": company,
            "started_at": now,
            "last_sent_at": now,
        }
    )
    _write_subscriptions(rows)


_scheduler_lock = threading.Lock()
_scheduler_started = False


def ensure_weekly_scheduler_running() -> None:
    """Starts, at most once per process, a daemon thread that resends each subscriber's report
    roughly every 7 days. Only runs while this Streamlit process stays alive -- see the module
    docstring."""
    global _scheduler_started
    with _scheduler_lock:
        if _scheduler_started:
            return
        _scheduler_started = True

    def _loop() -> None:
        while True:
            time.sleep(_POLL_SECONDS)
            rows = _read_subscriptions()
            if not rows:
                continue
            changed = False
            now = time.time()
            for row in rows:
                if now - row.get("last_sent_at", now) < WEEK_SECONDS:
                    continue
                pdf_path = Path(row.get("pdf_path", ""))
                if not pdf_path.is_absolute():
                    pdf_path = ROOT_DIR / pdf_path
                if not pdf_path.exists():
                    continue
                success, _ = send_digest_email(
                    row["email"],
                    pdf_path.read_bytes(),
                    pdf_path.name,
                    subject=f"Beacon AI weekly trend digest - {row.get('company') or 'your analysis'}",
                    body="Your weekly Beacon AI trend digest is attached.",
                )
                if success:
                    row["last_sent_at"] = now
                    changed = True
            if changed:
                _write_subscriptions(rows)

    thread = threading.Thread(target=_loop, daemon=True, name="beacon-ai-weekly-digest")
    thread.start()
