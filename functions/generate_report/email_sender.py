import logging
import os

import resend

from config import load_config
from email_template import render_email

logger = logging.getLogger(__name__)


def send_report_email(
    subscribers: list[dict],
    project: dict,
    report: dict,
    report_id: str,
):
    config = load_config()
    resend.api_key = os.environ["RESEND_API_KEY"]
    from_email = config["from_email"]
    site_url = config["site_url"]

    subject = f"{config['name']}: {report.get('title', project['name'])}"

    api_url = (
        f"https://{config['gcp_region']}-{config['gcp_project']}"
        f".cloudfunctions.net/api"
    )

    for sub in subscribers:
        html = render_email(report, report_id, sub["unsubscribe_token"], site_url)
        unsub_url = f"{site_url}/unsubscribe.html?token={sub['unsubscribe_token']}"
        unsub_api = f"{api_url}/unsubscribe?token={sub['unsubscribe_token']}"
        try:
            resend.Emails.send(
                {
                    "from": from_email,
                    "to": sub["email"],
                    "subject": subject,
                    "html": html,
                    "headers": {
                        "List-Unsubscribe": f"<{unsub_api}>",
                        "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
                    },
                }
            )
        except Exception:
            logger.exception("Failed to send email to %s", sub["email"])
