"""
Sends the HTML digest via SendGrid.
Requires env vars: SENDGRID_API_KEY, EMAIL_FROM, EMAIL_TO
"""

import os
import logging
import requests

log = logging.getLogger(__name__)

SENDGRID_URL = "https://api.sendgrid.com/v3/mail/send"


def send_email(subject: str, html_body: str) -> bool:
    api_key  = os.environ["SENDGRID_API_KEY"]
    from_email = os.environ["EMAIL_FROM"]      # must be a verified sender in SendGrid
    to_email   = os.environ["EMAIL_TO"]

    payload = {
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {"email": from_email, "name": "Apartment Agent"},
        "subject": subject,
        "content": [{"type": "text/html", "value": html_body}],
    }

    resp = requests.post(
        SENDGRID_URL,
        json=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        timeout=15,
    )

    if resp.status_code in (200, 202):
        log.info(f"Email sent to {to_email} (HTTP {resp.status_code})")
        return True
    else:
        log.error(f"SendGrid error {resp.status_code}: {resp.text}")
        return False
