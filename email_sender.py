import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from config import settings


def send_email(
    to_email: str,
    subject: str,
    body: str,
    from_email: Optional[str] = None,
) -> bool:
    if not settings.smtp_username or not settings.smtp_password:
        return False

    from_email = from_email or settings.smtp_username

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = from_email
    message["To"] = to_email

    html_body = body.replace("\n", "<br>")
    part1 = MIMEText(body, "plain", "utf-8")
    part2 = MIMEText(f"<html><body>{html_body}</body></html>", "html", "utf-8")
    message.attach(part1)
    message.attach(part2)

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(settings.smtp_server, settings.smtp_port) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(settings.smtp_username, settings.smtp_password)
            server.sendmail(from_email, to_email, message.as_string())
        return True
    except Exception:
        return False


def send_bulk_emails(recipients: list[dict]) -> list[dict]:
    results = []
    for r in recipients:
        success = send_email(
            to_email=r["email"],
            subject=r["subject"],
            body=r["body"],
        )
        results.append({
            "email": r["email"],
            "lead_id": r.get("lead_id"),
            "success": success,
        })
    return results
