import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.config import settings


class EmailNotConfiguredError(Exception):
    pass


def send_email(to: str, subject: str, html_body: str) -> None:
    if not settings.smtp_host or not settings.smtp_user or not settings.smtp_password:
        raise EmailNotConfiguredError(
            "SMTP is not configured — set SMTP_HOST, SMTP_USER, SMTP_PASSWORD "
            "(and EMAIL_FROM) in .env."
        )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.email_from
    msg["To"] = to
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.starttls()
        server.login(settings.smtp_user, settings.smtp_password)
        server.sendmail(settings.email_from, [to], msg.as_string())


def send_password_reset_email(to: str, reset_url: str) -> None:
    send_email(
        to=to,
        subject="Reset your Clipping Engine password",
        html_body=f"""
        <p>Someone requested a password reset for this account.</p>
        <p><a href="{reset_url}">Click here to reset your password</a> — this link expires in 1 hour.</p>
        <p>If you didn't request this, you can safely ignore this email.</p>
        """,
    )


def send_verification_email(to: str, verify_url: str) -> None:
    send_email(
        to=to,
        subject="Verify your email — Clipping Engine",
        html_body=f"""
        <p>One more step — confirm this is your email address.</p>
        <p><a href="{verify_url}">Click here to verify your email</a></p>
        """,
    )
