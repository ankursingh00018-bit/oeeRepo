"""
Email notification tool. Sends a real email via SMTP so a work order /
incident summary can be delivered to the responsible person after a human
approves the AI agent's recommended action.

Configure via environment variables (see .env.example):
    SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD,
    SMTP_FROM_EMAIL (optional, defaults to SMTP_USERNAME),
    SMTP_USE_SSL (optional, "true"/"false", default "true" for port 465)
"""
import os
import smtplib
import ssl
from email.message import EmailMessage
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models
from ..ws_manager import manager

router = APIRouter(prefix="/api/notify", tags=["notify"])


class EmailNotifyRequest(BaseModel):
    # Left optional (was previously required) -- when omitted, send_email()
    # sends to every saved recipient (see routers/recipients.py / the
    # Recipients page) instead of a single hard-coded address. Still
    # accepted so an explicit one-off address keeps working if ever needed.
    to_email: Optional[str] = None
    subject: str
    body: str
    incident_id: Optional[str] = None
    work_order_id: Optional[str] = None
    # Which machine this email relates to. Optional so older/other callers
    # don't break, but AgentContext.tsx always sends it now -- it's what
    # lets the "Email sent..." line get broadcast into the right machine's
    # chat log on every connected tab (see the email_sent/email_failed
    # broadcasts below), instead of only ever being visible on whichever
    # device happened to make this REST call (which, for the automated
    # pipeline, is the /control page -- a page that never even renders the
    # chat drawer, so that log line was previously unseeable by anyone).
    machine_id: Optional[str] = None


def _smtp_config():
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "465"))
    username = os.getenv("SMTP_USERNAME")
    password = os.getenv("SMTP_PASSWORD")
    from_email = os.getenv("SMTP_FROM_EMAIL", username)
    use_ssl = os.getenv("SMTP_USE_SSL", "true").lower() == "true"

    missing = [
        name for name, val in [
            ("SMTP_HOST", host), ("SMTP_USERNAME", username), ("SMTP_PASSWORD", password)
        ] if not val
    ]
    if missing:
        raise HTTPException(
            500,
            f"Email is not configured on the server. Missing env vars: {', '.join(missing)}. "
            f"Set them in manufacturing_ai_agent/.env (see .env.example) and restart the API.",
        )
    return host, port, username, password, from_email, use_ssl


@router.post("/email")
def send_email(body: EmailNotifyRequest, db: Session = Depends(get_db)):
    host, port, username, password, from_email, use_ssl = _smtp_config()

    # Explicit to_email (if ever passed) still works as a one-off override,
    # but normally this is empty and we email every saved recipient instead
    # of a single fixed address -- see routers/recipients.py.
    if body.to_email:
        to_emails = [body.to_email]
    else:
        to_emails = [r.email for r in db.query(models.Recipient).all()]

    if not to_emails:
        raise HTTPException(
            400,
            "No notification recipients configured. Add at least one on the "
            "Recipients page before sending.",
        )

    msg = EmailMessage()
    msg["Subject"] = body.subject
    msg["From"] = from_email
    msg["To"] = ", ".join(to_emails)
    msg.set_content(body.body)

    try:
        if use_ssl:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(host, port, context=context, timeout=15) as server:
                server.login(username, password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=15) as server:
                server.starttls(context=ssl.create_default_context())
                server.login(username, password)
                server.send_message(msg)
    except Exception as e:
        if body.machine_id:
            manager.broadcast_from_thread({
                "type": "email_failed",
                "machine_id": body.machine_id,
                "incident_id": body.incident_id,
                "work_order_id": body.work_order_id,
                "to_email": ", ".join(to_emails),
                "error": str(e),
            })
        raise HTTPException(502, f"Failed to send email: {e}")

    if body.machine_id:
        # Broadcast so the "Email sent..." line shows up live in the chat
        # log on every connected tab -- not just wherever this REST call
        # happened to originate from.
        manager.broadcast_from_thread({
            "type": "email_sent",
            "machine_id": body.machine_id,
            "incident_id": body.incident_id,
            "work_order_id": body.work_order_id,
            "to_email": ", ".join(to_emails),
        })

    return {
        "sent": True,
        "to_email": to_emails,
        "subject": body.subject,
        "incident_id": body.incident_id,
        "work_order_id": body.work_order_id,
    }
