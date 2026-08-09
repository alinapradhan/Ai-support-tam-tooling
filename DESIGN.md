# Design Note

## Failure modes

**1. Hallucinated or mis-parsed structured output.** The LLM could return malformed JSON, invent a
knowledge-base doc that doesn't exist, or fabricate a "quote" in the account brief that isn't actually
in the source ticket. Detection: `llm_client.call_llm_json` strictly parses JSON and raises on failure
rather than silently accepting garbage; the eval harness (Task 3) explicitly re-verifies every risk-flag
quote against the raw ticket body byte-for-byte (`require_quote_substring_from_tickets`). Mitigation: on
a parse failure, `triage.py` and `account_brief.py` fail safe to a deterministic rule-based fallback and
flag `needs_human_review=True` rather than surfacing a broken or fabricated result to an agent or TAM.

**2. Silent misclassification on ambiguous input.** A vague ticket ("thing is broken again") could be
confidently assigned a wrong urgency, sending it to the wrong queue or under-prioritizing a real issue.
Detection: the triage schema includes explicit `confidence` and `needs_human_review` fields, and the eval
suite has a dedicated adversarial case (`T1-06-ADVERSARIAL`) asserting low confidence and human-review on
vague input. Mitigation: the prompt explicitly instructs the model to prefer `"Ambiguous"` + low confidence
over a false-confident guess.

**3. Stale or incomplete knowledge-base retrieval.** BM25 is keyword-based, so it can miss KB docs that are
semantically relevant but lexically different (e.g. a ticket that never says "sync" but describes the exact
DBP-4402 symptom). Detection: track `kb_matches` count over time in the eval report; a sustained drop in
KB-match rate on categories that should have KB coverage is a regression signal. Mitigation: BM25 was a
deliberate choice at this corpus size (see below), but the retrieval layer is isolated in `src/retrieval.py`
specifically so it can be swapped for embedding-based search later without touching triage/brief logic.

## Latency vs quality trade-off

The concrete trade-off made was **BM25 keyword retrieval instead of an embedding + vector-DB pipeline** for
the knowledge-base lookup in Task 1. Embeddings would likely catch a few more semantically-related matches,
but at ~9 short KB docs, the quality delta is marginal while the latency and infrastructure cost (embedding
calls, a vector store, index maintenance) is not — BM25 runs in milliseconds with zero external calls. If
latency became the hard constraint at the *account brief* end instead, the next thing to cut would be the
single LLM call per brief in favor of the rule-based fallback path that's already built (`_mock_brief`) for
routine/healthy accounts, reserving the LLM call for accounts flagged At Risk/Churning where the extra
judgment quality actually matters.

## Data sensitivity

Ticket bodies and account data (contact names, titles, ARR, escalation notes) are plausible PII/business-
sensitive content. This design sends that data to the Anthropic API as part of the prompt, which is the
same trust boundary as any other LLM-powered internal tool — so the mitigations are: (1) all secrets live in
`.env`, never committed (`.env.example` only ships placeholders, and `.env` is gitignored); (2) no ticket or
account data is logged to disk or third-party services outside the single API call itself; (3) `MOCK_MODE`
lets the entire pipeline run with zero data leaving the machine, which is useful for local development or
processing genuinely sensitive accounts under stricter policy; (4) in a real production version, the next
step would be a PII-scrubbing pass (redacting names/emails before the prompt, restoring them post-response)
and a documented Anthropic data-retention/zero-retention agreement for this workload.

## Scaling

At 10x ticket volume (5,000 tickets), the KB retrieval (BM25 over ~9 docs) and per-ticket LLM call still
scale linearly and are not the bottleneck individually — but **sequential per-ticket LLM calls become the
bottleneck** for any batch/backlog processing use case (e.g. re-triaging a large backlog), since each call
is a network round-trip. What breaks first is single-threaded throughput: the current `triage_ticket()` is
synchronous and un-batched. The fix is straightforward and doesn't require redesigning the pipeline — add
async/concurrent request batching (e.g. `asyncio.gather` with a concurrency cap) in a batch-processing
wrapper around the existing function, plus basic rate-limit/backoff handling. The account-brief path scales
similarly per-account and would benefit from the same treatment before a QBR cycle that touches many accounts
at once.
