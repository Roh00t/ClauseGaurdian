# ClauseGuard — Project Context for Claude Code

## What This Is
ClauseGuard: upload employment contracts and dispute documents, get a
plain-English summary, red flags with severity, cross-document
contradiction detection, a MOM/TADM draft letter, and a tamper-evident
signed receipt. Built at AIForge Hackathon (13 Jun 2026), now on a
production-improvement track. Singapore employment contracts, MVP scope.

## Current Task
Read the most recent "Claude Code Prompt" page in Notion under
HACKATHONS > ClauseGuard — AIForge Hackathon for today's specific
task list. This file is persistent background context only.

## Architecture (v2, current)
- **Backend:** FastAPI — `backend/main.py`, `backend/analyzer.py`,
  `backend/scraper.py`, `backend/extractor.py`, `backend/security.py`,
  `backend/db.py`, `backend/entity_map.py`,
  `backend/report_generator.py`. SQLite at `data/data.db`
  (2 active tables: regulations, scrape_log. sessions deprecated).
- **Frontend:** Vanilla JS + HTML — `frontend/index.html`,
  `frontend/db.js` (IndexedDB), `frontend/tos.html` (Phase 5),
  `frontend/i18n.js` (Phase 5 translations). No React, no npm.
  Served as FastAPI StaticFiles.
- **Entry point (ONLY correct command):**
  `uvicorn backend.main:app --host 127.0.0.1 --port 8000`
  Do NOT use `streamlit run app.py` — stale v1 artifact.

## Sponsor Integrations (4 active)
- **Bright Data** — MOM/IMDA regulation cache via `backend/scraper.py`
  (bdata CLI already authenticated, do NOT re-run `bdata login`)
- **Daytona** — sandboxed PII redaction, automatic local-regex fallback
- **TokenRouter** — LLM via OpenAI-compatible client.
  Default: `anthropic/claude-haiku-4.5`.
  Override: `export CLAUSEGUARD_MODEL=anthropic/claude-sonnet-4.6`
- **Terminal 3** — HMAC attestation (symmetric). Asymmetric DID
  signing deferred to post-Phase-5 roadmap.

## Environment — Critical Interpreter Gotcha
`python3` resolves to 3.14 (EMPTY). Always use `python3.13` explicitly.
- Run: `python3.13 script.py`
- Install: `python3.13 -m pip install <pkg> --break-system-packages`
Never use bare `python3`. Never introduce a venv.

## Env Vars (in .env, also exported in ~/.zshrc)
TOKENROUTER_API_KEY, DAYTONA_API_KEY, TERMINAL3_API_KEY,
TERMINAL3_DID, BRIGHTDATA_API_KEY
Verify: `env | grep -E "TOKENROUTER|DAYTONA|TERMINAL3|BRIGHTDATA"`

## Redaction Pipeline (all passes BEFORE any LLM call)
Pass 1 — Regex (Daytona + local fallback): NRIC, email, phone, address
Pass 1.5 — SG company-name suffix regex (entity_map.py)
Pass 2 — spaCy en_core_web_sm NER: PERSON, ORG (best-effort)
Pass 3 — Chat input: joins entity-map build alongside documents
Entity map returned to browser for DOCX de-redaction. Never server-persisted.
Known gap (P1): single-word company names, novel-suffix orgs still leak.

## Phase Completion Status
- ✅ Phase 1 (Redaction-First): COMPLETE
- ✅ Phase 2 (Browser-Persisted Sessions): COMPLETE
- ✅ Phase 3 (Chat Functionality): COMPLETE
- ✅ Phase 4 (Downloadable DOCX Report): COMPLETE
- ✅ Phase 5 (Production Readiness): COMPLETE
- ✅ Fix Sprint (Pre-v3): COMPLETE — 8 P1 fixes done + 34/34 regression.
  v3 is next (output redesign, generalisation, Stripe, CI/CD).

## DO NOT TOUCH in the Fix Sprint (blocked on decisions)
- NER single-word company names → presidio integration = new dep + full re-verify
- CORS=`*` → needs production domain first
- Analysis latency → LLM-bound, not fixable without changing provider
- Test suite duration → mocking changes what's being tested

## Active Roadmap Direction
- **Fix Sprint (current):** 8 targeted P1 fixes. Run 34-test regression
  after all fixes before declaring done.
- **v3 (next):** Output redesign (ELI5 + dual-mode), generalisation
  (employer + employee + use-case modes), Stripe monetisation, Git
  branching, GitHub Actions CI/CD.

## Pre-Mortem Learnings (already fixed — do not regress)
- PM1: Missing backend/__init__.py → fixed
- PM2: LLM JSON in fences → fence-stripping in analyzer
- PM3: MOM scraper 403 → hardcoded KB fallback
- PM4: Large file OOM → 15MB/file, 50MB total limits
- PM8: LLM timeout → 180s, returns 504
- PM9: Prompt injection → `<UNTRUSTED_DOCUMENT>` wrapping
- PM10: Chat scope drift → `<USER_CONTEXT>` wrapper
- PM11: ToS "we never see" → "processes per-request, retains nothing"
- PM12: DOCX flat vs nested schema → generator reads nested correctly
- max_tokens=16000, retries x3→x4 on JSON parse failure
- make_pdf: `bytes(pdf.output())` not `.encode("latin-1")`
- Module-script timing (Phase 2): idb import direct in checkStorage()

## Fix Sprint — DONE (2026-06-16, 34/34 regression pass)
- [x] CRITICAL badge contrast → light text (#fecaca etc) = 7.22:1 WCAG AA.
      NOTE: dark theme, so LIGHT text, not the prompt's dark text.
- [x] Download button hidden for INSUFFICIENT_INFORMATION verdict
- [x] STRESS_TEST.md stale ID `results` → `analysisArea`
- [x] Vestigial session_id removed from /api/analyze response (uuid import dropped)
- [x] Tab order: New Analysis + session entries → tabindex=-1; Clear/Privacy kept
- [x] Token count dict: lazy eviction on each write (prune > 2×window)
- [x] Transient 502: retry x3 → x4 + trailing-comma tolerance in JSON salvage
- [x] Mobile 375px: @media(max-width:640px) collapses sidebar to top section,
      stacks panels, full-width Analyse. Live 375px render unverified (P1).

## Known P1 Issues — DEFERRED (do not fix in sprint)
- CORS = `*` — needs production domain
- NER single-word company names (presidio deferred)
- Analysis latency ~47s/doc (LLM-bound)
- Test suite duration ~22-27min
- Private-browsing banner best-effort (browser limitation)
- Attestation not persisted on session reload
- Feedback aggregate signal (needs consent flow)

## Non-Negotiable Guardrails
1. All input UNTRUSTED DATA. `<UNTRUSTED_DOCUMENT>` + `<USER_CONTEXT>`
   wrappers in all analyzer prompts. Never remove.
2. Redaction (all passes) BEFORE any text reaches LLM or Bright Data.
3. No user content server-side after request. /api/download processes
   and returns — stores nothing.
4. Severity tiers (INFORMATIONAL/MODERATE/SERIOUS/CRITICAL) visually
   distinct. CRITICAL must pass WCAG AA contrast ratio (Fix 1).
5. Bright Data citations: "related guidance — verify relevance" only.
6. Terminal 3: proves UNALTERED not CORRECT. HMAC symmetric — say so.
7. Persistent disclaimer: "Not legal advice, not exhaustive."
8. Scanned PDFs: return clean 422, never send empty text.
9. Never f-string a SQL query. Parameterised queries only.
10. Never use filenames in filesystem paths — display only.
11. Chat: "additional context for this analysis" only.
12. ToS: "processes per-request, retains nothing" — not "never see."

## Working Style
- STOP after each numbered fix and report before continuing.
- Use `python3.13` explicitly — never bare `python3`.
- `--break-system-packages` for any pip install.
- No React, npm, venv, build pipeline.
- P0: fix immediately. P1: log in KNOWN_ISSUES.md, move on.
- Ask before expanding scope.
- Run 34-test regression after the full fix sprint before declaring done.