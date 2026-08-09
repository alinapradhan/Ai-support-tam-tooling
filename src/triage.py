"""
Task 1: Intelligent ticket triage agent.

triage_ticket() is the callable entry point (also exposed via FastAPI in main.py).
"""

from __future__ import annotations

from src import llm_client
from src.retrieval import get_kb
from src.schemas import TriageResult, KBMatch
from prompts.triage_v1 import SYSTEM_PROMPT, build_user_prompt

TEAM_ROUTING = {
    "Bug": "Tier-2 Engineering Support",
    "Performance": "Tier-2 Engineering Support",
    "Integration": "Integrations Team",
    "Data Loss": "Tier-3 / Incident Response",
    "Billing": "Billing Ops",
    "Onboarding": "Customer Onboarding",
    "How-To": "Tier-1 Support",
    "Feature Request": "Product Team",
    "Ambiguous": "Tier-1 Support (triage review)",
}


def _mock_triage(subject: str, body: str, kb_context_docs) -> dict:
    """
    Deterministic rule-based fallback used when no ANTHROPIC_API_KEY is configured
    (MOCK_MODE). Keeps the repo runnable end-to-end without secrets, per the
    'must run from clean install' requirement, and gives CI something to test against.
    Real production behavior uses the LLM path below.
    """
    text = f"{subject} {body}".lower()

    is_vague = len(text.split()) < 12

    if any(w in text for w in ["data loss", "lost data", "deleted permanently"]):
        category, urgency = "Data Loss", "P1"
    elif any(w in text for w in ["switch", "competitor", "cancel", "churn", "leadership", "escalate"]):
        category, urgency = "Bug", "P1"
    elif any(w in text for w in ["timeout", "timed out", "timing out", "slow", "performance"]):
        category, urgency = "Performance", "P1" if ("timeout" in text or "timing out" in text) else "P2"
    elif any(w in text for w in ["invoice", "charged", "billing", "renewal", "budget"]):
        category, urgency = "Billing", "P3"
    elif any(w in text for w in ["how do i", "how to", "checklist", "onboarding"]):
        category = "Onboarding" if "onboarding" in text else "How-To"
        urgency = "P4"
    elif any(w in text for w in ["feature", "would be great", "request"]):
        category, urgency = "Feature Request", "P4"
    elif any(w in text for w in ["not working", "broken", "stopped", "fail"]):
        category, urgency = "Bug", "P2"
    else:
        category, urgency = "Ambiguous", "P3"

    if is_vague:
        category = "Ambiguous"

    kb_matches = [
        {"doc_path": d.path, "doc_title": d.title, "reason": "Keyword/BM25 match on ticket content."}
        for d in kb_context_docs
    ]

    return {
        "product_area": "Unclassified" if is_vague else "General",
        "issue_category": category,
        "urgency": urgency,
        "urgency_reasoning": "Rule-based mock classification (MOCK_MODE) based on keyword signals.",
        "kb_matches": kb_matches,
        "recommended_team": TEAM_ROUTING.get(category, "Tier-1 Support"),
        "draft_first_response": (
            "Hi there, thanks for reaching out - we've logged your ticket and a member of our "
            f"{TEAM_ROUTING.get(category, 'support')} team will follow up shortly."
            if not is_vague else
            "Hi there, thanks for reaching out. Could you share a few more details (error messages, "
            "when this started, steps to reproduce) so we can route this to the right team quickly?"
        ),
        "confidence": 0.4 if is_vague else 0.7,
        "needs_human_review": is_vague,
    }


def triage_ticket(subject: str, body: str) -> TriageResult:
    kb = get_kb()
    kb_docs = kb.search(f"{subject} {body}", top_k=2)
    kb_context = kb.as_prompt_context(kb_docs)

    if llm_client.MOCK_MODE:
        raw = _mock_triage(subject, body, kb_docs)
    else:
        user_prompt = build_user_prompt(subject, body, kb_context)
        try:
            raw = llm_client.call_llm_json(SYSTEM_PROMPT, user_prompt)
        except ValueError:
            # LLM failed to return parseable JSON -> fail safe to human review
            # rather than surfacing a broken/partial triage to the agent.
            raw = _mock_triage(subject, body, kb_docs)
            raw["needs_human_review"] = True
            raw["confidence"] = 0.2
            raw["urgency_reasoning"] = "LLM output could not be parsed; falling back to safe defaults."

    raw.setdefault("kb_matches", [])
    return TriageResult(**raw)
