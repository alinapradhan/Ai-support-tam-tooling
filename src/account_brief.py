"""
Task 2: TAM account health summariser.

generate_account_brief() is the callable entry point.

Determinism: temperature=0 on the LLM call, plus we hash the exact serialized
inputs (account + tickets) into `input_hash` on the output so the eval harness
and reviewers can verify that identical input -> identical output.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from src import llm_client
from src.data_access import get_account, get_tickets_for_account
from src.schemas import AccountBrief, RiskFlag
from prompts.account_brief_v1 import SYSTEM_PROMPT, build_user_prompt

RISK_KEYWORDS = {
    "Churn Signal": ["switch", "competitor", "cancel", "churn", "evaluating"],
    "Budget/Renewal": ["budget", "renewal", "renew", "finance", "cut"],
    "Escalation": ["escalate", "leadership", "urgent", "vp ", "director"],
}


def _hash_inputs(account: dict | None, tickets: list[dict]) -> str:
    payload = json.dumps({"account": account, "tickets": tickets}, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _mock_brief(account: dict | None, tickets: list[dict]) -> dict:
    """Deterministic rule-based fallback for MOCK_MODE (no API key required)."""
    if not account:
        return {
            "executive_summary": "No account record found for the given account_id. "
                                  "Cannot generate a brief without account data.",
            "risks_and_flags": [],
            "recommended_talking_points": [],
        }

    flags = []
    for t in tickets:
        body_lower = t["body"].lower()
        for risk_type, keywords in RISK_KEYWORDS.items():
            if any(k in body_lower for k in keywords):
                words = t["body"].split()
                quote = " ".join(words[:20])
                flags.append({
                    "ticket_id": t["ticket_id"],
                    "risk_type": risk_type,
                    "quote": quote,
                    "explanation": f"Ticket language matches '{risk_type}' risk pattern.",
                })
                break
        if t.get("satisfaction_score") is not None and t["satisfaction_score"] <= 2:
            words = t["body"].split()
            flags.append({
                "ticket_id": t["ticket_id"],
                "risk_type": "Satisfaction",
                "quote": " ".join(words[:20]),
                "explanation": f"Low satisfaction score ({t['satisfaction_score']}/5) on this ticket.",
            })

    summary = (
        f"{account['company']} is on the {account['plan_tier']} plan "
        f"(${account['arr_usd']:,} ARR) with health status '{account['health_status']}' "
        f"and a '{account['usage_trend']}' usage trend. "
        f"There are {account['open_tickets']} open tickets and {account['p1_tickets_last_30d']} "
        f"P1 tickets in the last 30 days. Renewal is due {account['renewal_date']}."
    )

    talking_points = []
    if account["health_status"] in ("At Risk", "Churning"):
        talking_points.append(
            f"Proactively address reliability concerns before the {account['renewal_date']} renewal."
        )
    if account["usage_trend"] in ("Declining", "Inactive"):
        talking_points.append("Discuss adoption blockers and identify underused seats/products.")
    if account["p1_tickets_last_30d"] > 0:
        talking_points.append(f"Review root cause of the {account['p1_tickets_last_30d']} recent P1 ticket(s).")
    if account.get("nps_score") is not None and account["nps_score"] <= 6:
        talking_points.append(f"Follow up on low NPS score ({account['nps_score']}/10).")
    if not talking_points:
        talking_points.append("Account is healthy - reinforce value delivered and explore expansion.")

    return {
        "executive_summary": summary,
        "risks_and_flags": flags,
        "recommended_talking_points": talking_points,
    }


def generate_account_brief(account_id: str) -> AccountBrief:
    account = get_account(account_id)
    tickets = get_tickets_for_account(account_id, days=90)
    input_hash = _hash_inputs(account, tickets)

    if llm_client.MOCK_MODE:
        raw = _mock_brief(account, tickets)
    else:
        account_json = json.dumps(account or {}, indent=2)
        tickets_json = json.dumps(tickets, indent=2)
        user_prompt = build_user_prompt(account_json, tickets_json)
        try:
            raw = llm_client.call_llm_json(SYSTEM_PROMPT, user_prompt, max_tokens=2000, temperature=0.0)
        except ValueError:
            raw = _mock_brief(account, tickets)
            raw["executive_summary"] = (
                "[LLM output could not be parsed; falling back to rule-based summary] "
                + raw["executive_summary"]
            )

    return AccountBrief(
        account_id=account_id,
        company=account["company"] if account else "Unknown",
        executive_summary=raw["executive_summary"],
        risks_and_flags=[RiskFlag(**f) for f in raw.get("risks_and_flags", [])],
        recommended_talking_points=raw.get("recommended_talking_points", []),
        generated_at=datetime.now(timezone.utc).isoformat(),
        input_hash=input_hash,
    )
