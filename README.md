# Support & TAM Copilot

Production-style AI tooling for two internal teams: **Technical Support** (ticket triage) and
**Technical Account Management** (account health briefs), built for the US Delivery Internship
technical task round.

- **Task 1** — Ticket Triage Agent → `src/triage.py`
- **Task 2** — TAM Account Health Summariser → `src/account_brief.py`
- **Task 3** — Evaluation Harness → `eval/run_eval.py`
- **Task 4** — Design Note → [`DESIGN.md`](./DESIGN.md)
- **Bonus** — Streamlit UI (`app.py`), CI eval (`.github/workflows/eval.yml`), prompt versioning (`prompts/`)

---

## Setup

```bash
git clone <this-repo-url>
cd support-tam-copilot
python3 -m venv .venv && source .venv/bin/activate   # optional but recommended
pip install -r requirements.txt

cp .env.example .env
# edit .env and add ANTHROPIC_API_KEY
```

Without an API key, the pipeline still runs end-to-end in **MOCK_MODE** (deterministic, rule-based
fallback) — useful for CI, for reviewers without a key, or for quick local testing. Set
`MOCK_MODE=1` in `.env` (or as an env var) to force it even with a key present.

## Single entry point

```bash
uvicorn main:app --reload
```
Then open `http://127.0.0.1:8000/docs` for interactive API docs.

## Sample run — Task 1 (Ticket Triage)

As a Python function:
```python
from src.triage import triage_ticket

result = triage_ticket(
    subject="DataBridge sync failing every night at 2am",
    body="Our nightly DataBridge Pro sync job to NetSuite has failed for the last 4 nights "
         "in a row with error code DBP-4402. Please escalate.",
)
print(result.model_dump_json(indent=2))
```

Or via the REST API:
```bash
curl -X POST http://127.0.0.1:8000/triage \
  -H "Content-Type: application/json" \
  -d '{"subject": "DataBridge sync failing every night", "body": "Sync to NetSuite fails nightly with DBP-4402, please escalate."}'
```

## Sample run — Task 2 (Account Brief)

```python
from src.account_brief import generate_account_brief

brief = generate_account_brief("ACC-1001")
print(brief.model_dump_json(indent=2))
```

```bash
curl http://127.0.0.1:8000/account-brief/ACC-1001
```

## Task 3 — Running the eval harness

```bash
python -m eval.run_eval
```
Writes `eval/eval_report.json` and `eval/eval_report.md`. Runs in whatever mode `.env` is set to
(MOCK or live LLM). CI (`.github/workflows/eval.yml`) always runs it in `MOCK_MODE=1` so pull
requests don't require secrets.

## Bonus: Streamlit UI

```bash
streamlit run app.py
```
A thin UI for triaging a ticket or generating an account brief without touching the API directly.

## Repo structure

```
support-tam-copilot/
├── data/                       # tickets.json, accounts.json (synthetic sample - swap for real dataset)
├── knowledge-base/             # product/troubleshooting/billing/onboarding markdown docs
├── prompts/                    # versioned prompts (triage_v1.py, account_brief_v1.py) + CHANGELOG.md
├── src/
│   ├── schemas.py              # Pydantic models for all structured outputs
│   ├── llm_client.py           # Anthropic API wrapper + MOCK_MODE fallback
│   ├── retrieval.py            # BM25 retrieval over the knowledge base
│   ├── data_access.py          # ticket/account loading helpers
│   ├── triage.py               # Task 1
│   └── account_brief.py        # Task 2
├── eval/
│   ├── test_cases.json         # 6 triage cases + 7 account-brief cases, incl. adversarial
│   ├── run_eval.py             # Task 3 harness
│   ├── eval_report.json        # generated
│   └── eval_report.md          # generated
├── main.py                     # FastAPI entry point
├── app.py                      # Streamlit UI (bonus)
├── DESIGN.md                   # Task 4
├── requirements.txt
└── .env.example
```

## Design note

See [`DESIGN.md`](./DESIGN.md) for failure modes, the latency-vs-quality trade-off, PII/data-sensitivity
handling, and scaling behavior at 10x volume.


POST METHOD :
<img width="817" height="258" alt="image" src="https://github.com/user-attachments/assets/b8427739-f5b3-40af-a4bf-363961af3863" />


GET METHOD:
<img width="848" height="329" alt="image" src="https://github.com/user-attachments/assets/532595e5-fc71-4c69-a31c-6add455d7533" />


