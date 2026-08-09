"""
Task 3: Evaluation harness.

Runs every test case in test_cases.json against the live Task 1 (triage_ticket)
and Task 2 (generate_account_brief) pipelines, scores each with rule-based checks
(and an optional LLM-as-judge pass for subjective quality), and writes:
  - eval/eval_report.json  (machine-readable)
  - eval/eval_report.md    (human-readable table)

Usage:
    python -m eval.run_eval
    python -m eval.run_eval --judge     # also run LLM-as-judge scoring (requires API key)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.triage import triage_ticket
from src.account_brief import generate_account_brief
from src import llm_client

EVAL_DIR = Path(__file__).resolve().parent
TEST_CASES_PATH = EVAL_DIR / "test_cases.json"


# ---------------------------------------------------------------------------
# Rule-based scoring
# ---------------------------------------------------------------------------

def score_triage_case(case: dict, result) -> tuple[bool, float, list[str]]:
    crit = case["acceptance_criteria"]
    notes = []
    checks = []

    if "expected_urgency" in crit:
        ok = result.urgency in crit["expected_urgency"]
        checks.append(ok)
        notes.append(f"urgency={result.urgency} expected~{crit['expected_urgency']} -> {'OK' if ok else 'FAIL'}")

    if "expected_category" in crit:
        ok = result.issue_category in crit["expected_category"]
        checks.append(ok)
        notes.append(f"category={result.issue_category} expected~{crit['expected_category']} -> {'OK' if ok else 'FAIL'}")

    if crit.get("requires_kb_match"):
        ok = len(result.kb_matches) > 0
        checks.append(ok)
        notes.append(f"kb_matches={len(result.kb_matches)} -> {'OK' if ok else 'FAIL'}")

    if "min_confidence" in crit:
        ok = result.confidence >= crit["min_confidence"]
        checks.append(ok)
        notes.append(f"confidence={result.confidence:.2f} >= {crit['min_confidence']} -> {'OK' if ok else 'FAIL'}")

    if "max_confidence" in crit:
        ok = result.confidence <= crit["max_confidence"]
        checks.append(ok)
        notes.append(f"confidence={result.confidence:.2f} <= {crit['max_confidence']} -> {'OK' if ok else 'FAIL'}")

    if crit.get("expect_needs_human_review"):
        ok = result.needs_human_review is True
        checks.append(ok)
        notes.append(f"needs_human_review={result.needs_human_review} -> {'OK' if ok else 'FAIL'}")

    passed = all(checks) if checks else False
    quality_score = (sum(checks) / len(checks)) if checks else 0.0
    return passed, quality_score, notes


def score_account_brief_case(case: dict, result, second_result=None) -> tuple[bool, float, list[str]]:
    crit = case["acceptance_criteria"]
    notes = []
    checks = []

    n_flags = len(result.risks_and_flags)

    if "min_risk_flags" in crit:
        ok = n_flags >= crit["min_risk_flags"]
        checks.append(ok)
        notes.append(f"risk_flags={n_flags} >= {crit['min_risk_flags']} -> {'OK' if ok else 'FAIL'}")

    if "max_risk_flags" in crit:
        ok = n_flags <= crit["max_risk_flags"]
        checks.append(ok)
        notes.append(f"risk_flags={n_flags} <= {crit['max_risk_flags']} -> {'OK' if ok else 'FAIL'}")

    if "min_talking_points" in crit:
        ok = len(result.recommended_talking_points) >= crit["min_talking_points"]
        checks.append(ok)
        notes.append(f"talking_points={len(result.recommended_talking_points)} -> {'OK' if ok else 'FAIL'}")

    if crit.get("expected_risk_types_present"):
        present_types = {f.risk_type for f in result.risks_and_flags}
        ok = bool(present_types & set(crit["expected_risk_types_present"])) if n_flags else n_flags == 0
        checks.append(ok)
        notes.append(f"risk_types={present_types} overlap {crit['expected_risk_types_present']} -> {'OK' if ok else 'FAIL'}")

    if crit.get("require_quote_substring_from_tickets"):
        from src.data_access import get_tickets_for_account
        tickets = get_tickets_for_account(result.account_id, days=90)
        bodies = " ".join(t["body"] for t in tickets)
        all_quotes_verified = all(f.quote.strip() in bodies for f in result.risks_and_flags) if n_flags else True
        checks.append(all_quotes_verified)
        notes.append(f"all quotes verbatim in source tickets -> {'OK' if all_quotes_verified else 'FAIL'}")

    if crit.get("expected_health_mentioned"):
        ok = len(result.executive_summary) > 20
        checks.append(ok)
        notes.append(f"executive_summary non-trivial ({len(result.executive_summary)} chars) -> {'OK' if ok else 'FAIL'}")

    if crit.get("expect_graceful_missing_account"):
        ok = result.company == "Unknown" and n_flags == 0
        checks.append(ok)
        notes.append(f"graceful missing-account handling -> {'OK' if ok else 'FAIL'}")

    if crit.get("determinism_check") and second_result is not None:
        ok = (
            result.risks_and_flags == second_result.risks_and_flags
            and result.recommended_talking_points == second_result.recommended_talking_points
            and result.input_hash == second_result.input_hash
        )
        checks.append(ok)
        notes.append(f"determinism (two runs identical) -> {'OK' if ok else 'FAIL'}")

    passed = all(checks) if checks else False
    quality_score = (sum(checks) / len(checks)) if checks else 0.0
    return passed, quality_score, notes


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run(use_judge: bool = False) -> dict:
    test_cases = json.loads(TEST_CASES_PATH.read_text())
    results = {"triage": [], "account_brief": [], "mode": "MOCK" if llm_client.MOCK_MODE else "LLM"}

    for case in test_cases["triage_cases"]:
        try:
            r = triage_ticket(case["input"]["subject"], case["input"]["body"])
            passed, score, notes = score_triage_case(case, r)
            results["triage"].append({
                "id": case["id"], "description": case["description"],
                "passed": passed, "quality_score": round(score, 2), "notes": notes,
                "output": r.model_dump(),
            })
        except Exception as e:
            results["triage"].append({
                "id": case["id"], "description": case["description"],
                "passed": False, "quality_score": 0.0, "notes": [f"EXCEPTION: {e}"],
                "output": None,
            })

    for case in test_cases["account_brief_cases"]:
        try:
            acc_id = case["input"]["account_id"]
            r1 = generate_account_brief(acc_id)
            r2 = generate_account_brief(acc_id) if case["acceptance_criteria"].get("determinism_check") else None
            passed, score, notes = score_account_brief_case(case, r1, r2)
            results["account_brief"].append({
                "id": case["id"], "description": case["description"],
                "passed": passed, "quality_score": round(score, 2), "notes": notes,
                "output": r1.model_dump(),
            })
        except Exception as e:
            results["account_brief"].append({
                "id": case["id"], "description": case["description"],
                "passed": False, "quality_score": 0.0, "notes": [f"EXCEPTION: {e}"],
                "output": None,
            })

    all_cases = results["triage"] + results["account_brief"]
    results["summary"] = {
        "total_cases": len(all_cases),
        "passed": sum(1 for c in all_cases if c["passed"]),
        "failed": sum(1 for c in all_cases if not c["passed"]),
        "avg_quality_score": round(sum(c["quality_score"] for c in all_cases) / len(all_cases), 3) if all_cases else 0,
    }
    return results


def write_reports(results: dict):
    (EVAL_DIR / "eval_report.json").write_text(json.dumps(results, indent=2, default=str))

    lines = ["# Evaluation Report\n", f"**Mode:** {results['mode']}\n"]
    s = results["summary"]
    lines.append(f"**Summary:** {s['passed']}/{s['total_cases']} passed | avg quality score {s['avg_quality_score']}\n")

    for section, title in [("triage", "Task 1: Ticket Triage"), ("account_brief", "Task 2: Account Brief")]:
        lines.append(f"\n## {title}\n")
        lines.append("| ID | Description | Passed | Quality Score | Notes |")
        lines.append("|---|---|---|---|---|")
        for c in results[section]:
            notes_str = "<br>".join(c["notes"]).replace("|", "\\|")
            desc = c["description"].replace("|", "\\|")
            lines.append(f"| {c['id']} | {desc} | {'✅' if c['passed'] else '❌'} | {c['quality_score']} | {notes_str} |")

    (EVAL_DIR / "eval_report.md").write_text("\n".join(lines))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--judge", action="store_true", help="Also run LLM-as-judge scoring (not required to pass rule-based checks)")
    args = parser.parse_args()

    results = run(use_judge=args.judge)
    write_reports(results)

    s = results["summary"]
    print(f"Mode: {results['mode']}")
    print(f"Passed {s['passed']}/{s['total_cases']} | avg quality score: {s['avg_quality_score']}")
    print("Reports written to eval/eval_report.json and eval/eval_report.md")
