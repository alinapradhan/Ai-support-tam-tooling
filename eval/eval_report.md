# Evaluation Report

**Mode:** MOCK

**Summary:** 13/13 passed | avg quality score 1.0


## Task 1: Ticket Triage

| ID | Description | Passed | Quality Score | Notes |
|---|---|---|---|---|
| T1-01 | Clear P1 bug with repeated failure pattern (PIPELINE_STALLED) - should match DataBridge Pro KB doc | ✅ | 1.0 | urgency=P1 expected~['P1'] -> OK<br>category=Bug expected~['Bug'] -> OK<br>kb_matches=2 -> OK<br>confidence=0.70 >= 0.5 -> OK |
| T1-02 | Simple how-to question referencing GROUP_NOT_MAPPED - should be low urgency, Tier-1 routed | ✅ | 1.0 | urgency=P4 expected~['P3', 'P4'] -> OK<br>category=How-To expected~['How-To'] -> OK<br>kb_matches=2 -> OK<br>confidence=0.70 >= 0.5 -> OK |
| T1-03 | Churn-risk language should escalate urgency despite being phrased calmly | ✅ | 1.0 | urgency=P3 expected~['P1', 'P2', 'P3'] -> OK<br>category=Billing expected~['Billing', 'Bug'] -> OK<br>confidence=0.70 >= 0.3 -> OK |
| T1-04 | Performance/timeout issue tied to a known KB error code (ERR_CONNECTION_TIMEOUT on a stalled CloudSync job) | ✅ | 1.0 | urgency=P1 expected~['P1', 'P2'] -> OK<br>category=Performance expected~['Performance', 'Integration', 'Bug'] -> OK<br>kb_matches=2 -> OK<br>confidence=0.70 >= 0.5 -> OK |
| T1-05 | Feature request - should be low urgency, routed to Product | ✅ | 1.0 | urgency=P4 expected~['P3', 'P4'] -> OK<br>category=Feature Request expected~['Feature Request'] -> OK<br>kb_matches=2 -> OK<br>confidence=0.70 >= 0.4 -> OK |
| T1-06-ADVERSARIAL | Adversarial: extremely vague ticket with no real information - should NOT be confidently triaged | ✅ | 1.0 | category=Ambiguous expected~['Ambiguous', 'Bug'] -> OK<br>confidence=0.40 <= 0.6 -> OK<br>needs_human_review=True -> OK |

## Task 2: Account Brief

| ID | Description | Passed | Quality Score | Notes |
|---|---|---|---|---|
| T2-01 | At-risk account with clear churn language in tickets - should be flagged with verbatim quotes | ✅ | 1.0 | risk_flags=3 >= 1 -> OK<br>all quotes verbatim in source tickets -> OK<br>executive_summary non-trivial (210 chars) -> OK |
| T2-02 | Healthy account with no open risk tickets - should produce few/no risk flags | ✅ | 1.0 | risk_flags=0 <= 1 -> OK<br>all quotes verbatim in source tickets -> OK<br>executive_summary non-trivial (205 chars) -> OK |
| T2-03 | Churning account with budget-cut language - must be flagged as Budget/Renewal or Churn Signal | ✅ | 1.0 | risk_flags=2 >= 1 -> OK<br>risk_types={'Satisfaction', 'Budget/Renewal'} overlap ['Churn Signal', 'Budget/Renewal', 'Escalation'] -> OK<br>all quotes verbatim in source tickets -> OK |
| T2-04 | Account with repeated escalations requesting leadership call - should surface in talking points | ✅ | 1.0 | risk_flags=2 >= 1 -> OK<br>talking_points=4 -> OK<br>all quotes verbatim in source tickets -> OK |
| T2-05 | New account with minimal history - brief should still be well-formed and not fabricate risk | ✅ | 1.0 | risk_flags=0 <= 1 -> OK<br>talking_points=1 -> OK<br>all quotes verbatim in source tickets -> OK |
| T2-06-ADVERSARIAL | Adversarial: account_id with no matching account record - must degrade gracefully, not crash or fabricate | ✅ | 1.0 | risk_flags=0 <= 0 -> OK<br>graceful missing-account handling -> OK |
| T2-07-DETERMINISM | Adversarial/determinism: same account run twice must yield identical risk flags and talking points | ✅ | 1.0 | determinism (two runs identical) -> OK |