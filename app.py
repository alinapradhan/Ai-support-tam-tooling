"""
Bonus: thin Streamlit UI so a non-technical support agent or TAM can actually
use Task 1 and Task 2 without touching the API directly.

Run with: streamlit run app.py
"""

import streamlit as st

from src.triage import triage_ticket
from src.account_brief import generate_account_brief
from src.data_access import load_accounts
from src import llm_client

st.set_page_config(page_title="Support & TAM Copilot", layout="wide")

st.sidebar.title("Support & TAM Copilot")
mode = st.sidebar.radio("Choose a tool", ["Ticket Triage", "Account Brief"])
st.sidebar.caption(f"Mode: {'🔧 MOCK (rule-based, no API key)' if llm_client.MOCK_MODE else '🤖 LLM (' + llm_client.MODEL + ')'}")

if mode == "Ticket Triage":
    st.title("🎫 Ticket Triage")
    st.caption("Paste a raw support ticket to get an instant triage decision.")

    subject = st.text_input("Subject", placeholder="e.g. Sync job failing every night")
    body = st.text_area("Body", height=150, placeholder="Paste the full ticket body here...")

    if st.button("Triage this ticket", type="primary") and (subject or body):
        with st.spinner("Triaging..."):
            result = triage_ticket(subject, body)

        col1, col2, col3 = st.columns(3)
        col1.metric("Urgency", result.urgency)
        col2.metric("Category", result.issue_category)
        col3.metric("Confidence", f"{result.confidence:.0%}")

        if result.needs_human_review:
            st.warning("⚠️ Flagged for human review — the ticket is ambiguous or low-confidence.")

        st.subheader("Reasoning")
        st.write(result.urgency_reasoning)

        st.subheader("Recommended Team")
        st.write(result.recommended_team)

        if result.kb_matches:
            st.subheader("Matched Knowledge Base Docs")
            for m in result.kb_matches:
                st.markdown(f"- **{m.doc_title}** (`{m.doc_path}`) — {m.reason}")

        st.subheader("Draft First Response")
        st.text_area("Editable draft", value=result.draft_first_response, height=120)

else:
    st.title("📋 TAM Account Brief")
    st.caption("Generate a QBR-ready account brief in seconds.")

    accounts = load_accounts()
    options = {f"{a['company']} ({a['account_id']})": a["account_id"] for a in accounts}
    label = st.selectbox("Select account", list(options.keys()))
    account_id = options[label]

    if st.button("Generate brief", type="primary"):
        with st.spinner("Generating brief..."):
            brief = generate_account_brief(account_id)

        st.subheader("Executive Summary")
        st.write(brief.executive_summary)

        st.subheader(f"Risks & Flags ({len(brief.risks_and_flags)})")
        if brief.risks_and_flags:
            for f in brief.risks_and_flags:
                st.markdown(f"**{f.risk_type}** — ticket `{f.ticket_id}`")
                st.markdown(f"> {f.quote}")
                st.caption(f.explanation)
        else:
            st.info("No risk signals flagged for this account.")

        st.subheader("Recommended Talking Points")
        for tp in brief.recommended_talking_points:
            st.markdown(f"- {tp}")

        st.caption(f"Generated at {brief.generated_at} · input hash `{brief.input_hash}`")
