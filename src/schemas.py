"""
Structured output schemas shared across Task 1 (triage) and Task 2 (account brief).
Keeping these in one place makes it easy for the eval harness (Task 3) to validate
outputs against a single source of truth.
"""

from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field

Urgency = Literal["P1", "P2", "P3", "P4"]


# ---------------------------------------------------------------------------
# Task 1: Ticket Triage
# ---------------------------------------------------------------------------

class TicketInput(BaseModel):
    subject: str
    body: str
    account_id: Optional[str] = None
    company: Optional[str] = None


class KBMatch(BaseModel):
    doc_path: str
    doc_title: str
    reason: str = Field(..., description="Why this doc is relevant to the ticket")


class TriageResult(BaseModel):
    product_area: str
    issue_category: Literal[
        "Bug", "Feature Request", "How-To", "Performance",
        "Billing", "Integration", "Onboarding", "Data Loss", "Ambiguous"
    ]
    urgency: Urgency
    urgency_reasoning: str
    kb_matches: list[KBMatch] = Field(default_factory=list)
    recommended_team: str
    draft_first_response: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    needs_human_review: bool = Field(
        default=False,
        description="True when the ticket is ambiguous/incomplete enough that "
                    "auto-triage confidence is low and a human should double check.",
    )


# ---------------------------------------------------------------------------
# Task 2: TAM Account Health Brief
# ---------------------------------------------------------------------------

class RiskFlag(BaseModel):
    ticket_id: str
    risk_type: Literal["Churn Signal", "Escalation", "Reliability", "Budget/Renewal", "Satisfaction"]
    quote: str = Field(..., description="Direct quote from the ticket body justifying this flag")
    explanation: str


class AccountBrief(BaseModel):
    account_id: str
    company: str
    executive_summary: str
    risks_and_flags: list[RiskFlag]
    recommended_talking_points: list[str]
    generated_at: str
    input_hash: str = Field(
        ..., description="Hash of the exact inputs used, for determinism verification"
    )
