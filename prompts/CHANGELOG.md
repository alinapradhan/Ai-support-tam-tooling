# Prompt Changelog

## triage_v1 (2026-08-09)
- Initial version. Strict JSON schema, explicit P1-P4 urgency rubric, ambiguity handling
  via `needs_human_review` flag instead of forcing a guess on vague tickets.

## account_brief_v1 (2026-08-09)
- Initial version. Requires verbatim quotes for every risk flag (no paraphrased "quotes"),
  explicit instruction against fabricating tickets/quotes, explicit determinism instruction.

<!-- Add new entries above this line as prompts evolve. Bump the version suffix (v2, v3...)
     rather than editing v1 in place, so eval results stay comparable across prompt versions. -->
