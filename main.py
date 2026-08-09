"""
FastAPI entry point.

Run with:  uvicorn main:app --reload
Then see:  http://127.0.0.1:8000/docs for interactive API docs.
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from src.triage import triage_ticket
from src.account_brief import generate_account_brief
from src.schemas import TriageResult, AccountBrief

app = FastAPI(
    title="Support & TAM Copilot API",
    description="Internal tooling API: ticket triage (Task 1) and TAM account briefs (Task 2).",
    version="0.1.0",
)


class TriageRequest(BaseModel):
    subject: str
    body: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/triage", response_model=TriageResult)
def triage_endpoint(req: TriageRequest):
    if not req.subject.strip() and not req.body.strip():
        raise HTTPException(status_code=400, detail="subject and body cannot both be empty")
    return triage_ticket(req.subject, req.body)


@app.get("/account-brief/{account_id}", response_model=AccountBrief)
def account_brief_endpoint(account_id: str):
    return generate_account_brief(account_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
