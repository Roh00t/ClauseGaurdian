# ClauseGuard v2 — Known Issues

Captured during the Build Order + automated stress pass (2026-06-13).
**No P0 issues.** 25/25 automated tests pass; the real 5-doc Xcellink case
analyses end-to-end (HTTP 200, severity CRITICAL, 6 targeted red flags).

## Stress-test results (Part C)

| Test | Status | Notes |
|------|--------|-------|
| Health endpoint | PASS | |
| Regulations endpoint (>=4 regs) | PASS | 8 regs, cached |
| Non-PDF rejection (400) | PASS | |
| Fake PDF magic bytes rejection (400) | PASS | |
| Oversized file rejection (413) | PASS | |
| Too many files rejection (400) | PASS | >10 files |
| Blank PDF -> 422 (not 500) | PASS | |
| Single contract analysis | PASS | ~47s on Sonnet |
| Multi-file analysis | PASS | fixed a test-fixture em-dash bug (see below) |
| Session save after analysis | PASS | |
| Session retrieval by ID | PASS | |
| Unknown session -> 404 | PASS | |
| Prompt injection -> flags still found | PASS | injection ignored, flags produced |
| Huge PDF -> truncated not crashed | PASS | text capped at 8000 chars/doc |
| Path traversal filename -> safe | PASS | filename is display-only |
| SQL injection via session ID -> safe | PASS | parameterised queries |
| Regulations endpoint < 500ms | PASS | served from cache |
| Analysis completes < budget | PASS | single ~47s, 5-doc ~108s |
| 3 sequential analyses all succeed | PASS | |

## P1 issues (logged, not blocking)

- **Analysis latency.** Sonnet via TokenRouter: ~47s/single doc, ~108s/5 docs.
  Good for a demo, not instant. Set `CLAUSEGUARD_MODEL=anthropic/claude-haiku-4.5`
  to roughly halve it at a small quality cost. (Kimi K2.6 was ~190s — too slow —
  so the default model was switched to Sonnet, still via the TokenRouter key.)
- **Session auth.** Anyone who guesses an 8-char hex session ID can view that
  analysis. Acceptable for a hackathon; add real auth for production.
- **CORS = `*`.** Fine for a localhost demo; restrict the origin in production.
- **Rate limiting is per-IP.** Behind a NAT all users share one bucket. The
  automated suite raises the limit via `CLAUSEGUARD_RATE_LIMIT` (conftest) so it
  isn't throttled; production default is 5/min on `/api/analyze`.
- **Scraper fallback.** mom.gov.sg may 403 the `requests` fallback; the hardcoded
  KB (5 entries) guarantees the app never shows 0 regulations. 3 of 6 URLs
  scraped live on this run; the rest came from KB.
- **Scanned/image-only PDFs** return no text -> a clean 422, not a crash. Users
  need text-layer PDFs.
- **Deprecation warnings** (`on_event`, TestClient `httpx`) are cosmetic only.

## Deviations from the brief worth knowing

- **Model:** brief said Kimi-fallback / Anthropic-primary. Anthropic isn't keyed,
  and Kimi was too slow, so the analyzer routes to `anthropic/claude-sonnet-4.6`
  **through the existing TokenRouter key** — Claude quality/speed, no new key.
- **Test fixture fix:** the verbatim `make_pdf` helper crashed on a `—` (em-dash)
  because Helvetica is latin-1 only. `make_pdf` now maps Unicode punctuation to
  ASCII before rendering. No change to app behaviour.
- **`response_format=json_object`** is NOT used — TokenRouter/Kimi returned empty
  content with it. Robust fence-stripping + 8192 max_tokens is used instead.
