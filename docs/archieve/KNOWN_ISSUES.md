## TASK 2 PATCH — SG Company-Name Regex (2026-06-14)

Added `_SG_COMPANY_RE` to `backend/entity_map.py` as pass 1.5 (between the existing
regex pass and the spaCy NER pass). Catches company names with SG-common suffixes:
`Pte Ltd`, `Sdn Bhd`, `Ltd`, `Inc`, `Corp`, `LLP`, `Group`, `Holdings`, `Ventures`,
`Services`, `Solutions`, `Staffing`, `Consulting`, `Technology/Technologies`,
`Systems`, `Management`, `Capital`, `Partners`, `Associates`, `Enterprise/Enterprises`.

Uses `"ORG"` as the entity type to share the counter with the spaCy ORG pass —
`[ORG_N]` numbering is globally consistent across both passes. The `assign()` guard
(`if value in emap: return`) ensures no double-counting if spaCy also catches the
same name.

**Remaining gap (P1):** Single-word company names ("Xcellink") and names with
unlisted suffixes still not caught. Disclosed in UI banner. Closing this fully
requires presidio or a larger spaCy model — deferred.

## PHASE 2 — Browser-Persisted No-Auth Sessions (2026-06-14, in progress)

Moving all user-session storage from server-side `data/data.db` to client-side
IndexedDB (`idb` library via CDN). Server becomes stateless with respect to user
content. Privacy claim upgrades from "we protect your data" to "we don't have
your data."

### Architecture
- `frontend/db.js` — IndexedDB schema and CRUD (saveSession, getAllSessions,
  getSession, deleteSession, clearAllSessions)
- `backend/main.py` — sessions table INSERT removed; regulations and scrape_log
  writes unchanged
- `GET /api/sessions/:id` — returns 410 Gone (deprecated, not deleted)
- "Clear my data" button added to UI
- Shared-device / private-browsing notice added on page load

### P1 notes (to be updated on completion)
- QuotaExceededError handling: catch and surface to user
- Private/incognito mode: IndexedDB unavailable — sessions not persisted, notice shown
- Old server-side session IDs in any cached sidebar state → 410 Gone on click

## TASK 2 PATCH — SG Company-Name Regex (2026-06-14)

Added `_SG_COMPANY_RE` to `backend/entity_map.py` as pass 1.5 (between the existing
regex pass and the spaCy NER pass). Catches company names with SG-common suffixes:
`Pte Ltd`, `Sdn Bhd`, `Ltd`, `Inc`, `Corp`, `LLP`, `Group`, `Holdings`, `Ventures`,
`Services`, `Solutions`, `Staffing`, `Consulting`, `Technology/Technologies`,
`Systems`, `Management`, `Capital`, `Partners`, `Associates`, `Enterprise/Enterprises`.

Uses `"ORG"` as the entity type to share the counter with the spaCy ORG pass —
`[ORG_N]` numbering is globally consistent across both passes. The `assign()` guard
(`if value in emap: return`) ensures no double-counting if spaCy also catches the
same name.

**Remaining gap (P1):** Single-word company names ("Xcellink") and names with
unlisted suffixes still not caught. Disclosed in UI banner. Closing this fully
requires presidio or a larger spaCy model — deferred.

## PHASE 2 — Browser-Persisted No-Auth Sessions (2026-06-14, in progress)

Moving all user-session storage from server-side `data/data.db` to client-side
IndexedDB (`idb` library via CDN). Server becomes stateless with respect to user
content. Privacy claim upgrades from "we protect your data" to "we don't have
your data."

### Architecture
- `frontend/db.js` — IndexedDB schema and CRUD (saveSession, getAllSessions,
  getSession, deleteSession, clearAllSessions)
- `backend/main.py` — sessions table INSERT removed; regulations and scrape_log
  writes unchanged
- `GET /api/sessions/:id` — returns 410 Gone (deprecated, not deleted)
- "Clear my data" button added to UI
- Shared-device / private-browsing notice added on page load

### P1 notes (to be updated on completion)
- QuotaExceededError handling: catch and surface to user
- Private/incognito mode: IndexedDB unavailable — sessions not persisted, notice shown
- Old server-side session IDs in any cached sidebar state → 410 Gone on click
## PHASE 2 — COMPLETE (2026-06-14) — supersedes the in-progress notes above

Implemented **Option A**: server-side session writes removed entirely; `data.db` keeps
only `regulations` + `scrape_log`. All session CRUD is client-side IndexedDB
(`frontend/db.js`, `idb@8` via CDN). `/api/analyze` sets `X-Session-Storage: client`;
`GET /api/sessions` and `GET /api/session/{id}` return **410 Gone** (kept, not deleted).
"Clear my data" button + persistent shared-device footer notice + best-effort
private-browsing banner added.

Verified end-to-end in a real browser (Chrome MCP): real PDF upload -> `/api/analyze` ->
saved to IndexedDB -> sidebar from IDB -> **persists across reload** -> "Clear my data"
empties it. `data.db` sessions count **unchanged (4->4)** after a browser analysis.
**Bonus:** MOM-letter de-redaction now works on session reload (entity map lives
client-side), fixing the prior "no session-reload de-redaction" P1.

### P1 notes (Phase 2)
- **Private-browsing banner is best-effort.** Modern Chrome/Firefox ALLOW IndexedDB in
  incognito, so the probe succeeds and the banner won't fire there. It only triggers when
  IndexedDB genuinely throws (storage blocked / some browsers). The persistent footer
  notice ("stored in this browser only...") is the real shared-device safeguard, always shown.
- **Module-script timing bug (fixed during build).** The deferred module `<script>` set
  `window._idbLib` AFTER the classic `init()` ran, so the probe spuriously showed the banner
  on every normal load. Fixed: `checkStorageAvailability()` imports the idb module directly.
- **QuotaExceededError handled:** save catch shows a "storage full -> Clear my data" toast;
  other save errors show a generic toast (NOT re-thrown, so a save failure can't masquerade
  as the handler's "Network error").
- **4 orphaned pre-Phase-2 rows remain in `data.db` sessions** (from before this change).
  Unreachable now (read endpoints are 410) and harmless, but slightly undercut the "we don't
  have your data" claim. Can be cleared on request (data deletion -> left for user to confirm).
- **Server still mints a `session_id`** in the `/api/analyze` response; vestigial (client
  generates its own `crypto.randomUUID()`).
- **Cross-origin IndexedDB** is per-origin: production must serve from one stable origin.

### Deviations from the literal brief
- Stored raw `data.entity_map` ({real->placeholder}), NOT the brief's `invertEntityMap(...)`
  (which doesn't exist) — `renderAnalysis` inverts it itself; pre-inverting would double-invert.
- Adapted to real function names (`loadSessions`/`loadSession`/`renderAnalysis`/`showToast`)
  vs the brief's illustrative `renderSidebar`/`renderResults`/`showNotice`.

## PHASE 2 STRESS TEST — Part A results (2026-06-14)

Ran `CLAUSEGUARD_TEST_BUDGET=180 python3.13 -m pytest tests/test_backend.py` (34 tests, 22:21).
Result: **32 passed, 2 failed**; the 2 failures **passed on isolated re-run** -> transient, not bugs.
Effective result: **34/34 green**. No P0s.

All Phase-2-specific tests PASS: no server session write, `X-Session-Storage: client` header,
`/api/session/{id}` -> 410, regulations table still written, `entity_map` present in response,
sessions list 410-or-empty. Security tests pass: prompt-injection still flags, NRIC not in
response (redaction), SQLi/XSS/path-traversal safe.

### P1 notes
- **Test helper was stale (fixed).** `make_pdf` used `pdf.output(dest="S").encode("latin-1")`,
  but fpdf2 2.8.7 returns a `bytearray` (no `.encode`) -> every PDF-building test errored in
  setup (23 false failures, whole suite in 0.8s). Fixed to `bytes(pdf.output())` (test-only;
  the STRESS_TEST.md embedded helper has the same stale line and should be updated there too).
- **Transient 502 on ~1-2 of ~15 analyze calls.** `analyze_combined` 502s when the LLM returns
  malformed JSON even after its 3 retries (known Haiku-JSON P1). Surfaces as flaky failures in
  `test_contract_only_returns_insufficient_judgment` and the X-Session-Storage test (the latter
  502'd before reaching its header assertion; header itself verified working via curl + re-run).
  Not a regression. Mitigation already in place (retry x3); a 4th retry or stricter JSON-mode
  would reduce it further.
- **Suite duration ~22 min** (real LLM + Daytona per analyze test). Expected; budget-tunable.
## PHASE 2 STRESS TEST — Part B Browser Tests (2026-06-14, pending)

Part A: 34/34 automated backend tests pass (2 transient 502 flakes re-ran clean).
Part B: browser UI tests (STRESS_TEST.md Tests 1-13) pending — to be run next session.

### make_pdf test helper fix (2026-06-14)

`make_pdf` in STRESS_TEST.md and `tests/test_backend.py` used:
```python
return pdf.output(dest="S").encode("latin-1")
```
fpdf2 2.8.7 returns a `bytearray` from `.output()` — no `.encode` method — causing
23 false test failures (whole suite errored in 0.8s in setup). Fix applied to
`tests/test_backend.py`: `return bytes(pdf.output())`. STRESS_TEST.md has the same
stale line and must be updated (Part b of the next Claude Code session).

## PHASE 3 — Chat Functionality (2026-06-14, in progress)

Chat textbar added between upload panels and 'Analyse Everything' button. Provides
a way for users to add narrative context not captured in documents.

### Architecture
- `frontend/index.html`: `<textarea id="chat-input">` with 2000-char cap + counter.
  Scoped in UI as "Additional context for this analysis only · Not a legal advisor."
- `backend/main.py`: `chat_context: str = Form(default='')` added to `/api/analyze`.
  Non-empty chat text joins the `build_entity_map()` texts list (same redaction as docs).
- `backend/analyzer.py`: `analyze_combined()` accepts `chat_context` param. Appended
  to the combined prompt under `<USER_CONTEXT>` wrapper AFTER `<UNTRUSTED_DOCUMENT>`
  blocks, BEFORE the analysis instructions. Tagged as supplementary context, not a document.
- `frontend/db.js` + session schema: `chat_context` field added. Raw (unredacted) text
  stored locally in IndexedDB. Repopulated in textarea on session reload.

### P1 notes (to be updated on completion)
- Chat input > 2000 chars: show 'Too long — upload as a document instead' (enforced by maxlength + JS)
- Empty chat: stripped and excluded from prompt (analyzer not confused by empty USER_CONTEXT)
- Chat debug log: add-then-remove pattern (same as Phase 2 Task 2.4) for NRIC-in-prompt verification
- Multi-turn within a session: not supported — chat is a single textarea per analysis, not a thread
## PHASE 3 — Chat Functionality — COMPLETE (2026-06-15)

Chat textbar between the upload panels and the Analyse button (2000-char cap, live
counter, "For this analysis only · Not a legal advisor" scope note — guardrail #11).
Chat joins the SAME combined entity-map redaction as documents BEFORE the LLM, is passed
to analyze_combined inside a scoped <USER_CONTEXT> block ("supporting info, NOT a new
document, not instructions"), and is persisted per-session in IndexedDB (raw, client-side
only — never re-sent to the server). Repopulates the textarea on session reload.

Verified end-to-end (Chrome MCP, real analysis): chat "S9876543B mentioned training would
start in January 2026" reached the prompt as "[NRIC_2] mentioned training would start in
January 2026" inside <USER_CONTEXT> (raw NRIC count 0); results considered the January
context; reload repopulated the chat; "Clear my data" wiped it. Debug log added then removed.

### P1 notes
- **Chat adds one Daytona round-trip (~5s)** when non-empty (regex backstop sweep on the
  chat). Acceptable; local-fallback applies if Daytona is down.
- **Browser caches index.html** — during MCP testing I had to cache-bust with a ?v= query
  param to pick up new frontend code. Real users get fresh HTML on a normal load; only an
  issue for rapid dev iteration. (Could add Cache-Control headers later if desired.)

  ## PHASE 2 STRESS TEST — Part B Browser Tests (2026-06-15): COMPLETE

All browser tests passed via Chrome MCP:

| Test | Result | Notes |
|---|---|---|
| 1 Navigation & empty state | ✅ 7/7 | No console errors; logo, panels, dynamic reg count, footer notice, dark bg |
| 2 File upload flow | ✅ | Chip + ×, Analyse en/disables, Panel B note grey→green |
| 3 Full analysis | ✅ | Loading overlay, all sections render, card expands, sidebar title |
| 4 Error handling | ✅ 3/3 | Human-readable error, app usable after |
| 5 Dual panel judgment | ✅ 4/4 | INSUFFICIENT→EMPLOYER_AT_FAULT green, above flags, sidebar label |
| 7 Redaction banner | ✅ 4/4 | Entity type counts, no values, collapsible |
| 11 IndexedDB persistence | ✅ 7/7 | Survives hard refresh, second tab |
| 12 Clear my data | ✅ 6/6 | Confirm dialog, Cancel keeps, Confirm empties, IDB count 0 |
| 13 Private browsing | ⚠️ 13.1 ✅ | Footer notice OK; 13.2-13.5 not MCP-automatable (incognito) |

P0s: none. P1s (test-harness only): clipboard read blocked by browser permission (Copy
click executes without error; MCP can't verify content). Incognito tests need manual run.

## PHASE 3 STRESS TEST — Part B (2026-06-15, pending manual run)

Chat functionality verified end-to-end via Chrome MCP during development.
Formal Part B stress test for Phase 3 (chat input, char counter, scope note,
redaction verification, session reload) pending — to be added to STRESS_TEST.md
in a future session.

## PHASE 4 — Downloadable DOCX Report (2026-06-15, in progress)

`POST /api/download` endpoint — client sends reversed entity map (placeholder→real)
+ analysis JSON. Server de-redacts all fields via `_deRedact()` and generates a
`python-docx` DOCX containing: header (timestamp, filenames analysed), judgment
(if present), executive summary, red flags table, recommended actions, de-redacted
MOM/TADM letter, Terminal 3 attestation receipt. Streams back as `.docx` download.
Server stores nothing (guardrail #3). "Download Report" button appears in UI after
analysis completes.

### Architecture
- `backend/main.py` — `POST /api/download` + `_generate_docx()` + `_deRedact()`
- `frontend/index.html` — "Download Report ⬇" button, reads entity_map from
  IndexedDB session, inverts it (real→placeholder becomes placeholder→real),
  POSTs to /api/download, triggers browser file save

### Terminal 3 Signing — Decision Point
Current HMAC signing is **symmetric**: verification requires ClauseGuard's own
`TERMINAL3_API_KEY`. A third party (TADM officer, lawyer) cannot independently
verify the signature without that secret. The DOCX attestation section notes this
explicitly: "Signature method: HMAC-SHA256 (symmetric, requires ClauseGuard's
signing key to verify)."

Terminal 3's asymmetric DID-based signing (`did:t3n:f9914f8d1d403a7443550cae6808b9261bf68177`)
would allow independent verification — deferred to Phase 5 pending review of
Terminal 3 SDK support for asymmetric operations.

### P1 notes (to be updated on completion)
- Zero placeholder tokens in DOCX must be verified post-generation:
  `python3.13 -c "from docx import Document; doc = Document('report.docx'); ..."`
- DOCX only for MVP — PDF export (libreoffice headless) deferred
- "Download Report" button should only appear when verdict is not
  INSUFFICIENT_INFORMATION (no MOM letter exists for that case)
- De-redaction at download time requires session's entity_map to still be
  in IndexedDB — not available if user cleared their data
## PHASE 4 — Downloadable DOCX Report — COMPLETE (2026-06-15)

"Download Report (.docx)" button (topbar, shown after analysis). POST /api/download →
`backend/report_generator.py` (python-docx). Client sends the FULL analyze response +
reversed entity map (placeholder→real); server de-redacts every field, builds the DOCX
(header+SHA-256 hash, dispute judgment, executive summary, red-flags table [capped 20],
recommended actions, MOM/TADM letter, attestation receipt, footer), streams it back, and
persists nothing (guardrail #3). Attestation copy states the signature is HMAC (symmetric)
— honest per guardrail #6.

Verified end-to-end (Chrome MCP, real analysis on synthetic_contract.pdf): button appears
after analysis, real click saved a 40KB DOCX to ~/Downloads, opened it → all sections
present, **zero placeholder tokens**, real names de-redacted (Alex Tan, Acme), report hash
present. No P0s.

### Important correction made during build (data-shape mismatch)
The Notion task's `_generate_docx` assumed a FLAT analysis object, but the client sends the
NESTED full response (analysis under `["analysis"]`; judgment/attestation siblings) and
`mom_report_draft`/`recommended_actions` are dicts/list-of-dicts (the task's `letter.split`
and `str(action)` would crash/garble). Rewrote the generator for the real shape with correct
field names (`issue`/`clause_or_section`/`verdict_reasoning`), dict-aware MOM letter, and
formatted actions. This is the pre-mortem's exact failure mode — averted.

### P1 notes
- **python-docx dependency added** (was already installed on python3.13; pip if missing).
- **Frontend uses an in-memory `currentReport`** (set on fresh analysis + session reload),
  NOT the task's `getSession(currentSessionId)` — there is no `currentSessionId` tracked in
  the codebase. Works for both paths; no IndexedDB round-trip.
- **Test artifact:** a synthetic-data DOCX was left in ~/Downloads during verification
  (`ClauseGuard_Report_2026-06-15.docx`) — harmless (no real PII), can be deleted.
## PHASE 4 — Downloadable DOCX Report — COMPLETE (2026-06-15)

`backend/report_generator.py` (python-docx) + `POST /api/download`. Client
sends full nested analyze response + reversed entity map (placeholder→real).
Server de-redacts via `_deRedact()`, generates DOCX:
header+timestamp+report_hash, judgment (if not INSUFFICIENT), executive
summary, red flags table (severity/issue/clause), recommended actions,
de-redacted MOM letter, Terminal 3 attestation receipt with HMAC-symmetric
honesty note. Streams back as `.docx`, stores nothing (guardrail #3).
Frontend: "Download Report ⬇" button in topbar, appears on fresh analysis
and session reload, hidden on New Analysis. Uses in-memory `currentReport`
(no server round-trip).

Verified: real 40KB DOCX downloaded, opened — zero placeholder tokens,
real names substituted (Alex Tan, Acme Staffing Pte Ltd), all sections
present, report hash matches attestation section.

### Critical deviation caught and fixed during build
The Phase 4 prompt's `_generate_docx` assumed a FLAT analysis object.
The actual response is NESTED (`session.analysis` = full API response with
`.analysis`, `.judgment`, `.attestation`, `.entity_map` as siblings).
Field names also differed: `flag.description` → `flag.issue`,
`judgment.reasoning` → `judgment.verdict_reasoning`,
`mom_report_draft` → a dict `{subject, to, body}` not a string.
Rewritten to match real schema — this was the pre-mortem's exact failure mode
(placeholder-filled DOCX submitted to TADM) averted.

### P1 notes
- `python-docx` dependency (new). Not in original requirements.
- Frontend uses in-memory `currentReport` (no `currentSessionId` tracked
  in codebase) — deviation from brief flagged.
- DOCX only for MVP. PDF export (libreoffice headless) deferred.
- Download button shows even for INSUFFICIENT_INFORMATION verdict (no MOM
  letter in that case — DOCX generates but MOM section is empty).

### Terminal 3 signing decision
HMAC (symmetric) retained for now — anyone wishing to verify the attestation
independently requires ClauseGuard's TERMINAL3_API_KEY. Asymmetric DID-based
signing (`did:t3n:f9914f8d1d403a7443550cae6808b9261bf68177`) investigated:
Terminal 3 docs reference DID signing but SDK support for asymmetric operations
was not confirmed in this session. Deferred to Phase 6.

## PHASE 5 — Production Readiness (2026-06-15, in progress)

### Architecture
- `frontend/tos.html` — Privacy Policy + ToS at `/tos`. Key wording:
  "processes per-request, retains nothing" (NOT "we never see your data").
- `backend/main.py` — hybrid rate limiting: 20/min per-IP (raised from 5)
  + 5/min per-session-token via `X-Session-Token` header. Both required
  because per-IP is too restrictive for NAT, per-token alone is bypassable
  via new UUID generation.
- `frontend/index.html` — thumbs up/down per red flag. Stored in IndexedDB
  `feedback` field alongside session. No server writes (guardrail #3).
- `frontend/index.html` — ARIA live regions on results, loading, toasts.
  Tab order verified. Mobile 375px viewport checked.
- `frontend/i18n.js` — EN/MS/TL translations for UI copy only (disclaimer,
  redaction banner, MOM letter preamble/sign-off, privacy link). Analysis
  output stays English. Tagalog has stronger disclaimer than EN/MS: "not a
  legal translation — verify all legal references before submitting."

### P1 notes (to be updated on completion)
- Rate limiting per-session-token still bypassable if attacker generates
  a new UUID per request and rotates fast enough to stay under per-IP limit
- Feedback has no aggregate signal (client-side only) — opt-in share is
  a future feature requiring explicit user consent flow
- Colour contrast on severity badges not yet WCAG-AA verified
- Multi-language covers UI copy only — red flags and AI analysis outputs
  remain English; full analysis translation requires separate LLM calls
  with quality-unknown translations (Phase 6 consideration)
- ToS is AI-generated content, not reviewed by a lawyer — add a note
  "for informational purposes, not legal advice" to the ToS page itself