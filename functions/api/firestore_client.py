import hashlib
import hmac
import os
from datetime import datetime, timezone

from google.cloud import firestore


def _db():
    return firestore.Client(project=os.environ.get("GCP_PROJECT"))


def add_subscriber(email: str) -> tuple[str, str]:
    """Returns (status, confirmation_token)."""
    db = _db()
    existing = list(
        db.collection("subscribers").where("email", "==", email).limit(1).stream()
    )
    secret = os.environ["UNSUBSCRIBE_SECRET"]

    if existing:
        doc = existing[0]
        data = doc.to_dict()
        if data.get("confirmed") and data.get("active"):
            return "already_subscribed", ""
        if not data.get("active"):
            confirm_token = hmac.new(
                secret.encode(), f"confirm:{email}".encode(), hashlib.sha256
            ).hexdigest()
            doc.reference.update(
                {"active": True, "confirmed": False, "confirmation_token": confirm_token}
            )
            return "pending_confirmation", confirm_token
        confirm_token = data.get("confirmation_token", "")
        return "pending_confirmation", confirm_token

    unsub_token = hmac.new(
        secret.encode(), email.encode(), hashlib.sha256
    ).hexdigest()
    confirm_token = hmac.new(
        secret.encode(), f"confirm:{email}".encode(), hashlib.sha256
    ).hexdigest()
    db.collection("subscribers").add(
        {
            "email": email,
            "subscribed_at": datetime.now(timezone.utc),
            "unsubscribe_token": unsub_token,
            "confirmation_token": confirm_token,
            "confirmed": False,
            "active": True,
        }
    )
    return "pending_confirmation", confirm_token


def confirm_subscriber(token: str) -> bool:
    db = _db()
    docs = list(
        db.collection("subscribers")
        .where("confirmation_token", "==", token)
        .limit(1)
        .stream()
    )
    if not docs:
        return False
    docs[0].reference.update({"confirmed": True})
    return True


def remove_subscriber(token: str) -> bool:
    db = _db()
    docs = list(
        db.collection("subscribers")
        .where("unsubscribe_token", "==", token)
        .limit(1)
        .stream()
    )
    if not docs:
        return False
    docs[0].reference.update({"active": False})
    return True


def list_reports(limit: int = 20, start_after: str | None = None) -> list[dict]:
    db = _db()
    q = (
        db.collection("reports")
        .order_by("created_at", direction=firestore.Query.DESCENDING)
        .limit(limit)
    )
    if start_after:
        doc = db.collection("reports").document(start_after).get()
        if doc.exists:
            q = q.start_after(doc)

    results = []
    for doc in q.stream():
        d = doc.to_dict()
        d["id"] = doc.id
        for key in ("raw_markdown", "beginner", "intermediate", "advanced"):
            d.pop(key, None)
        if "created_at" in d and hasattr(d["created_at"], "isoformat"):
            d["created_at"] = d["created_at"].isoformat()
        results.append(d)
    return results


def get_latest_report() -> dict | None:
    db = _db()
    docs = list(
        db.collection("reports")
        .order_by("created_at", direction=firestore.Query.DESCENDING)
        .limit(1)
        .stream()
    )
    if not docs:
        return None
    d = docs[0].to_dict()
    d["id"] = docs[0].id
    if "created_at" in d and hasattr(d["created_at"], "isoformat"):
        d["created_at"] = d["created_at"].isoformat()
    return d


def get_report(report_id: str) -> dict | None:
    doc = _db().collection("reports").document(report_id).get()
    if not doc.exists:
        return None
    d = doc.to_dict()
    d["id"] = doc.id
    d.pop("raw_markdown", None)
    if "created_at" in d and hasattr(d["created_at"], "isoformat"):
        d["created_at"] = d["created_at"].isoformat()
    return d
