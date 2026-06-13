# ClauseGuard — Claude Code Build Handoff

You are taking over an in-progress hackathon project. Core pieces have
already been individually proven working (see "Proven Facts" below).
Your job is to assemble a real web application: FastAPI backend + a
simple HTML/JS frontend (no build step — plain HTML/CSS/vanilla JS or
htmx via CDN; do NOT introduce React/npm/Vite, there is no time budget
for a build pipeline). Read this entire document before writing code.

## Time Constraint & Working Style
We are inside a live hackathon with limited time remaining. After each
numbered step below, STOP, report what happened (worked / didn't /
output), and wait before continuing to the next step. Do not batch
multiple steps' changes together — if something breaks, we need to know
which step broke it. If you think the scope should expand beyond what's
listed here, ASK before doing it.

## Problem Statement
Employees signing fixed-term contracts, training bonds, and
government-linked traineeship agreements routinely face ambiguous bond
clauses, unsigned-but-enforced internal forms, and verbal claims that
contradict the written contract. Most employees can't tell which clauses
are enforceable, which are boilerplate, and which contradict current
employment law. ClauseGuard: upload a contract PDF, get a plain-English
summary, specific red flags with severity, live regulatory citations
where relevant, and a tamper-evident signed receipt of the analysis.

## Environment — Where Everything Already Is
- `TOKENROUTER_API_KEY`, `DAYTONA_API_KEY`, `TERMINAL3_API_KEY`,
  `TERMINAL3_DID` are exported in `~/.zshrc` (already sourced in this
  shell). Verify with `env | grep -E "TOKENROUTER|DAYTONA|TERMINAL3"`.
- Bright Data CLI (`bdata`) is already authenticated via `bdata login`
  (separate from any env var — don't re-auth, just call `bdata search "..."`).
- `python3` resolves to `/opt/homebrew/.../python3.13` — this is the
  interpreter with all packages installed (`openai`, `daytona`,
  `pdfplumber`, `streamlit`, `fpdf2`). Use this `python3` for everything;
  do not introduce a venv.

## Proven Facts (do not re-verify, build on these)
- `src/analyzer.py` — `analyze(text) -> dict` calling Kimi via TokenRouter
  (OpenAI-compatible client, `base_url="https://api.tokenrouter.com/v1"`,
  `model="moonshotai/kimi-k2.6"`). Returns clean JSON:
  `{clause_summary, plain_english_summary, red_flags: [{clause, issue, severity, regulation_lookup}]}`.
  TESTED AND WORKING.
- Daytona `daytona` SDK 0.186.0: `Daytona(DaytonaConfig(api_key=...))`,
  `daytona.create()`, `sandbox.process.code_run(script_string)`,
  `sandbox.fs.upload_file(bytes, path)`, `sandbox.delete()`. ALL TESTED
  AND WORKING. `pdfplumber` is NOT in the sandbox image — sandbox code
  must use stdlib only (`re`, `json`, `hashlib`).
- `src/terminal3_signer.py` — `sign_report_hash(hash) -> dict`, pure
  HMAC/stdlib, no network. WORKING.
- `generate_sample.py` — generates a synthetic fictional contract
  (Acme Staffing / Alex Tan) with seeded red flags. Fix the
  `multi_cell` empty-line bug (see top of this doc) if not already fixed.

## Re-Architected Pipeline (PII redaction is now CORE, not roadmap)

```
[Frontend: upload PDF]
   -> [Backend: pdfplumber extract text locally]
   -> [Daytona sandbox: regex-based PII redaction — stdlib `re` only,
       no extra installs needed. Redacts: Singapore NRIC pattern
       ([STFG]\d{7}[A-Z]), email addresses, phone numbers (SG formats),
       residential address patterns. Returns redacted_text + a
       redaction_report listing WHAT TYPES were redacted and counts
       (not the original values)]
   -> [Backend: show user the redacted text for confirmation before
       it leaves the machine for the LLM call]
   -> [Analyzer (Kimi/TokenRouter) on REDACTED text only]
   -> [For red flags tagged regulation_lookup=true (max 3): Bright Data
       `bdata search` for current MOM/IMDA-equivalent guidance]
   -> [Daytona sandbox (2nd call, can reuse pattern from sandbox_validate.py):
       hash the final report -> report_hash]
   -> [Terminal 3: sign report_hash]
   -> [Frontend: display redaction summary, plain-English summary,
       red flags w/ severity + citations, attestation receipt]
```

[Stretch, only if core works with time to spare] Set
`sandbox.network_block_all=True` (or equivalent config) on the redaction
sandbox specifically — PII redaction needs zero network access, and
proving that programmatically is a strong demo point. Check the
`daytona` SDK for how this is actually configured (it appeared as a
`Sandbox` attribute in earlier testing, but the create-time config API
wasn't verified).

## CRITICAL — Real Contract Upload Constraints
The user CAN upload a real contract (their own, redacted or not) for
this hackathon. You must implement, and the frontend must DISPLAY
PROMINENTLY:

1. **Before any upload**, a notice: "You can upload a real contract or
   use the demo contract. Automated redaction below is best-effort
   (catches NRIC numbers, emails, phone numbers, common address
   patterns) and is NOT guaranteed complete — it will not catch names
   in prose, signatures, or other identifying context. Do not upload a
   document containing information you would not want processed by a
   third-party AI service even after this redaction step."

2. **After redaction, before the LLM call**: show the redacted text (or
   a diff/highlight of what was redacted) and require the user to click
   "Continue" — an explicit confirmation step, not silent pass-through.

3. **No persistence**: do not write uploaded PDFs or extracted text to
   disk beyond what's needed for the request lifecycle. In-memory only.

## Red-Flag Checklist (seed list — already encoded in analyzer.py)
Ambiguous bond durations; bond clauses triggered by resignation that may
not exempt natural contract expiry; unsigned forms imposing financial
obligations; contradictions between sections; asymmetric notice periods;
discretionary leave framed as guaranteed; one-sided "company reserves the
right" clauses.

## Other Guardrails (from prior red-team — keep these)
- Analyzer system prompt must explicitly treat extracted document text
  as UNTRUSTED DATA, not instructions (already in analyzer.py — preserve
  this when modifying).
- Severity tiers (info/moderate/serious) must be visually distinct in
  the UI (already color-coded in the old Streamlit version — port the
  concept).
- Bright Data citations must be labeled "related guidance — verify
  relevance," not "proof."
- Terminal 3 signature must be labeled as proving the report is
  UNALTERED, not that the analysis is CORRECT.
- Persistent UI disclaimer: "Not legal advice, not exhaustive. A 'no red
  flags found' result does not guarantee a contract is fair. Singapore
  employment contracts (MVP scope)."
- Scanned/image PDFs: if `pdfplumber` extraction returns empty/near-empty
  text, show an explicit error ("this looks like a scanned PDF — text
  extraction failed") rather than sending empty text to the analyzer.

## Build Order
0. Fix `generate_sample.py` empty-line bug, run it, confirm
   `sample_data/synthetic_contract.pdf` exists.
1. Build `src/redactor.py` — Daytona sandbox script, stdlib regex
   redaction, returns `{redacted_text, redaction_report}`. Test
   standalone against the synthetic contract's extracted text.
2. Confirm `src/analyzer.py` still works against redacted text (should
   be unchanged, just different input).
3. Build `src/regulation_check.py` — `bdata search` subprocess wrapper,
   called per regulation-tagged flag, capped at 3.
4. FastAPI backend (`backend/main.py`): single `/analyze` endpoint
   (multipart PDF upload) orchestrating extract -> redact -> analyze ->
   regulation_check -> hash -> sign -> return JSON. Add a
   `/confirm-redaction` step if doing the two-phase confirmation as a
   second endpoint, OR do it as two calls to `/analyze` with a
   `confirmed: bool` flag — your choice, state which you picked.
5. Frontend (`frontend/index.html` + vanilla JS): upload form, redaction
   confirmation UI, results display with severity colors, attestation
   receipt, persistent disclaimer banner. Serve via FastAPI
   `StaticFiles` or a trivial `python3 -m http.server` — pick whichever
   is faster to get running.
6. End-to-end run on synthetic contract. Then end-to-end run on a real
   (user-provided) contract if time allows.
7. 3x dry run before demo.

## Demo Script (2 min)
Hook: "HR forms are written to be ambiguous on purpose. ClauseGuard
reads the fine print and tells you what they're hoping you won't notice
— and redacts your personal data before any of it leaves your machine."
Live: upload contract -> show redaction summary -> confirm -> red flags
appear with severity -> one flag shows live regulatory guidance -> show
signed receipt.
Close: "Every analysis is sandboxed for both privacy and tamper-evidence
— the report can't be edited after the fact, and your PII never reaches
the AI model."