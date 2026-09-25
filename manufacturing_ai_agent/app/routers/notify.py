"""
Email notification tool.

Sends transactional email through Brevo's HTTP API.

Configure via environment variables:

    BREVO_API_KEY
    BREVO_FROM_EMAIL
    BREVO_FROM_NAME

Brevo API:
    https://api.brevo.com/v3/smtp/email

The API uses HTTPS instead of SMTP, which avoids the SMTP
connection/timeout problem we were having with smtp.gmail.com.
"""

import os
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models
from ..ws_manager import manager


router = APIRouter(
    prefix="/api/notify",
    tags=["notify"],
)


# =========================================================================
# BREVO CONFIGURATION
# =========================================================================

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


# =========================================================================
# REQUEST MODEL
# =========================================================================

class EmailNotifyRequest(BaseModel):
    """
    Request body for sending an email notification.

    If to_email is provided:
        Send email only to that address.

    If to_email is not provided:
        Send email to all recipients stored in the database.
    """

    to_email: Optional[str] = None

    subject: str

    body: str

    incident_id: Optional[str] = None

    work_order_id: Optional[str] = None

    # Machine related to this notification.
    # Used for WebSocket broadcasting.
    machine_id: Optional[str] = None


# =========================================================================
# BREVO ENVIRONMENT CONFIGURATION
# =========================================================================

def _brevo_config():
    """
    Read Brevo configuration from environment variables.
    """

    api_key = os.getenv("BREVO_API_KEY")

    from_email = os.getenv("BREVO_FROM_EMAIL")

    from_name = os.getenv(
        "BREVO_FROM_NAME",
        "OEE Monitoring",
    )

    # Check required environment variables
    missing = [
        name
        for name, value in [
            ("BREVO_API_KEY", api_key),
            ("BREVO_FROM_EMAIL", from_email),
        ]
        if not value
    ]

    if missing:
        raise HTTPException(
            status_code=500,
            detail=(
                "Email is not configured on the server. "
                f"Missing environment variables: {', '.join(missing)}. "
                "Set them in Railway Variables and redeploy the application."
            ),
        )

    return api_key, from_email, from_name


# =========================================================================
# EMAIL NOTIFICATION ENDPOINT
# =========================================================================

@router.post("/email")
def send_email(
    body: EmailNotifyRequest,
    db: Session = Depends(get_db),
):
    """
    Send an email notification through Brevo.

    Flow:

        React
          ↓
        POST /api/notify/email
          ↓
        FastAPI
          ↓
        Brevo HTTP API
          ↓
        Recipient email
    """

    # ---------------------------------------------------------------------
    # Get Brevo configuration
    # ---------------------------------------------------------------------

    api_key, from_email, from_name = _brevo_config()

    # ---------------------------------------------------------------------
    # Determine recipients
    # ---------------------------------------------------------------------

    if body.to_email:

        # ---------------------------------------------------------------
        # Explicit recipient
        # ---------------------------------------------------------------

        to_emails = [
            body.to_email
        ]

    else:

        # ---------------------------------------------------------------
        # Get all recipients from database
        # ---------------------------------------------------------------

        to_emails = [
            recipient.email
            for recipient in db.query(models.Recipient).all()
            if recipient.email
        ]

    # ---------------------------------------------------------------------
    # Make sure at least one recipient exists
    # ---------------------------------------------------------------------

    if not to_emails:

        raise HTTPException(
            status_code=400,
            detail=(
                "No notification recipients configured. "
                "Add at least one recipient on the Recipients page "
                "before sending."
            ),
        )

    # =========================================================================
    # BREVO PAYLOAD
    # =========================================================================

    payload = {
        "sender": {
            "name": from_name,
            "email": from_email,
        },

        "to": [
            {
                "email": email,
            }
            for email in to_emails
        ],

        "subject": body.subject,

        "textContent": body.body,
    }

    # =========================================================================
    # SEND EMAIL THROUGH BREVO HTTP API
    # =========================================================================

    try:

        response = httpx.post(
            BREVO_API_URL,

            headers={
                "accept": "application/json",

                "api-key": api_key,

                "content-type": "application/json",
            },

            json=payload,

            timeout=15,
        )

        # -----------------------------------------------------------------
        # Raise an exception if Brevo returns 4xx or 5xx
        # -----------------------------------------------------------------

        response.raise_for_status()

        # -----------------------------------------------------------------
        # Parse Brevo response
        # -----------------------------------------------------------------

        try:

            response_data = response.json()

        except Exception:

            response_data = {}

        # Brevo normally returns messageId
        message_id = response_data.get("messageId")

    # =========================================================================
    # BREVO HTTP ERROR
    # =========================================================================

    except httpx.HTTPStatusError as e:

        detail = str(e)

        # Try to extract useful error message from Brevo
        try:

            error_data = e.response.json()

            if isinstance(error_data, dict):

                detail = error_data.get(
                    "message",
                    detail,
                )

                # Some Brevo errors may contain a code
                error_code = error_data.get("code")

                if error_code:

                    detail = f"{error_code}: {detail}"

        except Exception:

            pass

        # ---------------------------------------------------------------
        # Broadcast email failure
        # ---------------------------------------------------------------

        if body.machine_id:

            manager.broadcast_from_thread(
                {
                    "type": "email_failed",

                    "machine_id": body.machine_id,

                    "incident_id": body.incident_id,

                    "work_order_id": body.work_order_id,

                    "to_email": ", ".join(to_emails),

                    "error": detail,
                }
            )

        # ---------------------------------------------------------------
        # Return 502 to frontend
        # ---------------------------------------------------------------

        raise HTTPException(
            status_code=502,

            detail=(
                f"Brevo rejected the email request: {detail}"
            ),
        )

    # =========================================================================
    # NETWORK / TIMEOUT ERROR
    # =========================================================================

    except httpx.RequestError as e:

        detail = str(e)

        # ---------------------------------------------------------------
        # Broadcast failure
        # ---------------------------------------------------------------

        if body.machine_id:

            manager.broadcast_from_thread(
                {
                    "type": "email_failed",

                    "machine_id": body.machine_id,

                    "incident_id": body.incident_id,

                    "work_order_id": body.work_order_id,

                    "to_email": ", ".join(to_emails),

                    "error": detail,
                }
            )

        # ---------------------------------------------------------------
        # Return 502
        # ---------------------------------------------------------------

        raise HTTPException(
            status_code=502,

            detail=(
                f"Could not connect to Brevo API: {detail}"
            ),
        )

    # =========================================================================
    # UNEXPECTED ERROR
    # =========================================================================

    except Exception as e:

        detail = str(e)

        # ---------------------------------------------------------------
        # Broadcast failure
        # ---------------------------------------------------------------

        if body.machine_id:

            manager.broadcast_from_thread(
                {
                    "type": "email_failed",

                    "machine_id": body.machine_id,

                    "incident_id": body.incident_id,

                    "work_order_id": body.work_order_id,

                    "to_email": ", ".join(to_emails),

                    "error": detail,
                }
            )

        # ---------------------------------------------------------------
        # Return 502
        # ---------------------------------------------------------------

        raise HTTPException(
            status_code=502,

            detail=(
                f"Failed to send email: {detail}"
            ),
        )

    # =========================================================================
    # SUCCESS
    # =========================================================================

    if body.machine_id:

        manager.broadcast_from_thread(
            {
                "type": "email_sent",

                "machine_id": body.machine_id,

                "incident_id": body.incident_id,

                "work_order_id": body.work_order_id,

                "to_email": ", ".join(to_emails),
            }
        )

    # =========================================================================
    # RETURN RESPONSE
    # =========================================================================

    return {
        "sent": True,

        "provider": "brevo",

        "message_id": message_id,

        "to_email": to_emails,

        "subject": body.subject,

        "incident_id": body.incident_id,

        "work_order_id": body.work_order_id,
    }
    