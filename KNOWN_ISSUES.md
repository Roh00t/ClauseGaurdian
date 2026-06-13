# ClauseGuard — Known Issues (P1, non-blocking)

Captured during the pre-demo test pass (2026-06-13). No P0s found — all four
test PDFs (synthetic_contract, empty, injection, huge) completed and every
guardrail (empty-text error, PII redaction, untrusted-text/injection, regulation
cap) fired as designed. The items below are P1: working but suboptimal/cosmetic.
Do not fix unless P0 list is empty and time clearly allows.

- **PHONE redaction can over-match.** The 8-digit SG-phone regex may redact non-PII 8-digit numbers (e.g. contract/reference IDs) in real contracts. Best-effort by design; acceptable for MVP.
- **No token-limit guard on very large PDFs.** `/analyze` sends the full redacted text in one LLM call. The 10× "huge" PDF (~15k chars) worked, but a very large real contract could exceed the model context. No chunking yet.
- **Address redaction is shallow.** Only catches `#unit-num`, `Blk/Block N`, and 6-digit postal codes — not free-form street addresses or names in prose (already disclosed in the UI redaction notice).
- **TestClient deprecation warning** (`StarletteDeprecationWarning: install httpx2`) appears only in the test harness, not the uvicorn-served app. Cosmetic, test-only.
- **huge.pdf dedupes rather than scaling flags.** 10× repeated content yielded 5 flags (the model collapses duplicates) — arguably correct, noted for awareness.
