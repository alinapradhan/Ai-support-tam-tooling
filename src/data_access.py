from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

DATA_ROOT = Path(__file__).resolve().parent.parent / "data"


def load_tickets() -> list[dict]:
    return json.loads((DATA_ROOT / "tickets.json").read_text(encoding="utf-8"))


def load_accounts() -> list[dict]:
    return json.loads((DATA_ROOT / "accounts.json").read_text(encoding="utf-8"))


def get_account(account_id: str) -> Optional[dict]:
    for acc in load_accounts():
        if acc["account_id"] == account_id:
            return acc
    return None


def get_tickets_for_account(account_id: str, days: int = 90) -> list[dict]:
    """
    Returns tickets for the given account within the last `days` days.
    Handles missing/unmatched account_id gracefully (returns empty list) since
    the dataset intentionally contains tickets whose account_id has no matching
    account record.
    """
    now = datetime.now(timezone.utc)
    out = []
    for t in load_tickets():
        if t.get("account_id") != account_id:
            continue
        created = t.get("created_at")
        if not created:
            continue
        created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
        if (now - created_dt).days <= days:
            out.append(t)
    out.sort(key=lambda t: t["created_at"], reverse=True)
    return out
