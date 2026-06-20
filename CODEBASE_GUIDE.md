# ClauseGuard Codebase Architecture Guide

## Project Overview
ClauseGuard is a Singapore employment contract analyzer. Users upload employment contracts and dispute documents, get red-flag analysis, contradictions detection, and a tamper-evident DOCX report. Total codebase: ~1,900 lines across backend (Python) and frontend (vanilla JS).

**Tech Stack:**
- **Backend:** FastAPI (Python 3.13) — REST API at port 8000
- **Frontend:** Vanilla JS + HTML (no React, no npm) — served as static files
- **Database:** SQLite at `data/data.db`
- **Sponsor Integrations:** Bright Data (scraper), Daytona (redaction sandbox), TokenRouter (LLM), Terminal 3 (HMAC signing)

---

## Directory Structure

```
agentforgehackathon/
├── backend/                 # FastAPI app + core logic
│   ├── main.py             # Entry point — routes, request handling
│   ├── analyzer.py         # LLM calls → red flags + verdict
│   ├── extractor.py        # PDF text extraction (pdfplumber)
│   ├── redaction.py        # Orchestrates Daytona redaction (concurrent)
│   ├── entity_map.py       # Cross-doc PII placeholder mapping (NER + regex)
│   ├── scraper.py          # Bright Data integration — MOM regulation cache
│   ├── db.py               # SQLite connection + schema
│   ├── security.py         # File validation, size limits, sanitization
│   ├── report_generator.py # DOCX generation (python-docx)
│   └── __init__.py         # Package marker
│
├── frontend/               # Vanilla JS — client-side session storage
│   ├── index.html          # Main UI (single-page app, dark theme)
│   ├── db.js               # IndexedDB wrapper (idb library)
│   ├── tos.html            # Terms of service (Phase 5)
│   └── i18n.js             # Translations (Phase 5)
│
├── src/                    # Sponsor integrations (Daytona, Terminal 3)
│   ├── redactor.py         # Redaction engine (Daytona + local fallback)
│   ├── sandbox_validate.py # Daytona sandbox validation
│   ├── terminal3_signer.py # HMAC attestation (symmetric key)
│   ├── regulation_check.py # [Unused currently]
│   └── analyzer.py         # [Legacy v1, unused]
│
├── tests/                  # Pytest suite (34 tests, ~22-27 min runtime)
│   ├── conftest.py         # Fixtures, TestSession mock
│   ├── test_backend.py     # Main test suite
│   └── __init__.py
│
├── test/                   # Older ad-hoc tests (less maintained)
│   ├── test_daytona.py
│   ├── test_analyzer.py
│   ├── test_llm.py
│   └── test.py
│
├── data/
│   └── data.db             # SQLite (created on first run)
│
├── sample_data/            # Sample PDFs for stress testing
│
├── docs/                   # Documentation
│   ├── STRESS_TEST.md
│   ├── architecture/
│   └── ...
│
├── .env                    # Environment variables
├── CLAUDE.md               # Project context (read before major changes)
├── KNOWN_ISSUES.md         # P1 issues (deferred, not bugs)
└── [config files]
```

---

## Critical Data Flow: One Request from Start to Finish

### Request Path: `POST /api/analyze`

```
USER UPLOADS → BROWSER VALIDATION → HTTP Request (contract_files + context_files + chat_context)
                                                     ↓
                                    backend/main.py:analyze()
                                                     ↓
    ┌────────────────────────────────────────────────────────────────┐
    │ STEP 1: File Validation (security.py)                          │
    │ - Count check (≤10 files total)                                │
    │ - Size check (≤15MB/file, ≤50MB total)                         │
    │ - Extension check (contract: PDF only; context: PDF/TXT/EML)   │
    └────────────────────────────────────────────────────────────────┘
                                    ↓
    ┌────────────────────────────────────────────────────────────────┐
    │ STEP 2: Text Extraction (extractor.py)                         │
    │ - Contract PDFs → extract_text() → raw text per document       │
    │ - Context files → extract_context_text() → raw text            │
    │ - Empty PDF? Return 422 SCANNED_PDF error                      │
    │ Output: [{filename, text}, ...]                                │
    └────────────────────────────────────────────────────────────────┘
                                    ↓
    ┌────────────────────────────────────────────────────────────────┐
    │ STEP 3: Cross-Document Entity Mapping (entity_map.py)          │
    │ - NER (spaCy en_core_web_sm) → PERSON, ORG names               │
    │ - Regex (Daytona + local) → NRIC, email, phone, address        │
    │ - Build UNIFIED map: real_value → [PERSON_1], [ORG_1], etc.    │
    │ - Apply map to ALL documents + chat_context (same entities     │
    │   get same placeholders across docs)                           │
    │ Output: entity_map = {real_nric: "[NRIC_1]", ...}              │
    │         Returned to BROWSER for de-redaction (NOT to LLM)      │
    └────────────────────────────────────────────────────────────────┘
                                    ↓
    ┌────────────────────────────────────────────────────────────────┐
    │ STEP 4: Daytona Redaction (redaction.py → src/redactor.py)     │
    │ - Each document redacted CONCURRENTLY (ThreadPoolExecutor)     │
    │ - Redact sandbox for PII (Pass 1: regex from Daytona)          │
    │ - Fallback: local regex if sandbox timeout (45s per doc)       │
    │ - Output: {filename, text(redacted), engine: 'daytona'|'local' │
    └────────────────────────────────────────────────────────────────┘
                                    ↓
    ┌────────────────────────────────────────────────────────────────┐
    │ STEP 5: Bright Data Regulation Scraping (scraper.py, optional) │
    │ - Background: scrape MOM/TADM (Ministry) guidance              │
    │ - Return 3 best-matched regulations as context (NOT truth)     │
    │ Output: regulations = [{title, url, excerpt}, ...]             │
    └────────────────────────────────────────────────────────────────┘
                                    ↓
    ┌────────────────────────────────────────────────────────────────┐
    │ STEP 6: LLM Analysis (analyzer.py:analyze_combined)            │
    │ - Wrap each document in <UNTRUSTED_DOCUMENT> (hardening)       │
    │ - Wrap chat_context in <USER_CONTEXT>                          │
    │ - Call LLM (TokenRouter → claude-haiku-4.5 by default)         │
    │ - LLM returns:{red_flags[], verdict, judgment, recommendations}│
    │ - Timeout: 180s (returns 504 if hung)                          │
    │ Output: {analysisArea{red_flags, contradictions}, verdict}     │
    └────────────────────────────────────────────────────────────────┘
                                    ↓
    ┌────────────────────────────────────────────────────────────────┐
    │ STEP 7: Terminal 3 Attestation (src/terminal3_signer.py)       │
    │ - HMAC-SHA256 of analysis JSON (symmetric key, NOT signature)  │
    │ - Proves: "This JSON was not altered after signing"            │
    │ - Does NOT prove: "This analysis is correct"                   │
    │ Output: {analysis, attestation_hmac, attestation_timestamp}    │
    └────────────────────────────────────────────────────────────────┘
                                    ↓
    ┌────────────────────────────────────────────────────────────────┐
    │ STEP 8: Return to Browser                                      │
    │ - 200 OK + JSON: {analysisArea, regulations, entity_map}       │
    │ - entity_map = {real_value: placeholder} for DE-REDACTION only │
    │ - Browser IndexedDB (db.js): saveSession()                     │
    │ Output: Frontend displays red flags, verdict, recommendations  │
    └────────────────────────────────────────────────────────────────┘
                                    ↓
                        DOWNLOAD DOCX REPORT (GET /api/download)
                                    ↓
    ┌────────────────────────────────────────────────────────────────┐
    │ STEP 9: On-Demand Report Generation (report_generator.py)      │
    │ - Regenerate DOCX from saved analysis JSON + entity_map        │
    │ - De-redact PII using entity_map (swap placeholders back)      │
    │ - Terminal 3: include HMAC signature in document               │
    │ - Stateless: never persists user content                       │
    │ Output: .docx file (binary) → download to user machine         │
    └────────────────────────────────────────────────────────────────┘
```

---

## Key Files Explained (Read in This Order)

### 1. **backend/main.py** — Entry Point & Request Routing
**What it does:** 
- Creates FastAPI app with rate limiting (20/min per IP, 5/min per session token)
- Defines all HTTP routes
- Orchestrates the full analyze flow (calls analyzer, extractor, redaction, entity_map, etc.)
- Serves static frontend files

**Key endpoints:**
- `POST /api/analyze` — Main upload & analysis (lines 144-290+)
- `GET /api/sessions` — Returns last 30 analyses (sidebar)
- `GET /api/session/{id}` — Fetch one saved analysis
- `GET /api/download` — Generate DOCX from saved analysis
- `GET /` — Serves `frontend/index.html`

**Entry command:** `python3.13 -m uvicorn backend.main:app --host 127.0.0.1 --port 8000`

---

### 2. **backend/analyzer.py** — The Brain
**What it does:**
- Takes redacted documents + regulations
- Calls the LLM (TokenRouter → claude-haiku-4.5 by default, override with `CLAUSEGUARD_MODEL=anthropic/claude-sonnet-4.6`)
- Returns JSON: `{red_flags[], verdict, judgment, recommendations}`

**Key function:** `analyze_combined(redacted_docs, context_text, regulations)`
- Wraps every document in `<UNTRUSTED_DOCUMENT>` to prevent injection
- Timeout: 180s (returns 504 if hung)
- Retries on JSON parse failure (x4)

**LLM Output Format:**
```json
{
  "analysisArea": {
    "red_flags": [
      {"severity": "CRITICAL", "text": "...", "reasoning": "..."},
      {"severity": "SERIOUS", "text": "...", "reasoning": "..."},
      ...
    ],
    "contradictions": [{"doc1": "...", "doc2": "...", "issue": "..."}],
    "verdict": "POTENTIAL_UNDERPAYMENT|INSUFFICIENT_INFORMATION|...",
    "judgment": "...",
    "recommendations": ["...", ...]
  }
}
```

---

### 3. **backend/extractor.py** — PDF Text Extraction
**What it does:**
- `extract_text(file_bytes, filename)` → {filename, text, pages, chars, success, error?}
- Uses `pdfplumber` library
- Returns error if PDF is scanned (no extractable text) → 422 response

**Key outputs:**
- `success: True` → text extracted, ready for redaction
- `success: False` → scanned PDF, no OCR available, user told to convert first

---

### 4. **backend/redaction.py** — Daytona Orchestration
**What it does:**
- Calls `src/redactor.py:redact()` for each document CONCURRENTLY (no serialization)
- Per-document timeout: 45s (if Daytona sandbox hangs, falls back to local regex)
- Always succeeds (never raises) — returns redacted text + engine used

**Key output:**
```python
{
  "filename": "contract.pdf",
  "text": "redacted text with [NRIC_1], [EMAIL_1], ...",
  "redaction_report": {NRIC: 3, EMAIL: 1, ...},
  "total_redactions": 4,
  "engine": "daytona" | "local"
}
```

---

### 5. **backend/entity_map.py** — Cross-Document PII Mapping
**What it does:**
- Builds a UNIFIED entity map from ALL documents + chat context
- Pass 1 (regex): NRIC, email, phone, address via Daytona + local regex
- Pass 1.5 (regex): SG company-name suffixes (Pte Ltd, Ltd, etc.)
- Pass 2 (spaCy NER): PERSON, ORG names
- Ensures same entity → same placeholder across ALL documents

**Key function:** `build_entity_map(texts: list[str]) → {real_value: placeholder}`
```python
entity_map = {
  "+65 9123 4567": "[PHONE_1]",
  "Alice Wong": "[PERSON_1]",
  "Tech Corp Pte Ltd": "[ORG_1]",
  ...
}
```

**Critical guardrail:** This map is returned to the BROWSER for de-redaction in the DOCX report, but NEVER sent to LLM or Bright Data.

---

### 6. **backend/db.py** — SQLite Schema & Connection
**What it does:**
- Single file: `data/data.db`
- Two active tables: `regulations` (MOM cache), `scrape_log` (Bright Data calls)
- One deprecated table: `sessions` (moved to browser IndexedDB in Phase 2)

**Key functions:**
- `get_conn()` → returns thread-safe SQLite connection
- `init_db()` → idempotent schema creation
- `migrate_db()` → upgrade old DBs (rarely used)

**Schema (current):**
```sql
CREATE TABLE regulations (
  id INTEGER PRIMARY KEY,
  url TEXT NOT NULL UNIQUE,
  title TEXT,
  content TEXT,
  category TEXT,
  scraped_at TEXT
);

CREATE TABLE scrape_log (
  id INTEGER PRIMARY KEY,
  regulation_url TEXT,
  queried_at TEXT,
  success BOOLEAN
);
```

---

### 7. **backend/security.py** — Validation & Sanitization
**What it does:**
- `validate_file(filename, content)` → checks extension, size, type
- `MAX_FILE_SIZE_BYTES = 15 * 1024 * 1024` (15MB per file)
- `MAX_TOTAL_SIZE_BYTES = 50 * 1024 * 1024` (50MB total)
- `MAX_FILES = 10` (contract + context combined)
- `sanitise_for_llm(text)` → strips dangerous patterns

---

### 8. **backend/scraper.py** — Bright Data Integration
**What it does:**
- `get_regulations(query)` → queries MOM/TADM rules
- Hardcoded KB fallback if API unavailable (handles 403)
- Returns 3 best-matched regulations as context (labeled "related guidance — verify relevance")

**Important:** These are suggestions only, not authoritative truth.

---

### 9. **backend/report_generator.py** — DOCX Generation
**What it does:**
- `generate_docx(analysis_json, entity_map, filenames)` → DOCX bytes
- De-redacts PII by swapping [PERSON_1] → "Alice Wong" using entity_map
- Includes Terminal 3 HMAC signature in footer
- Stateless: reads input, returns output, stores nothing

**Output:** Binary DOCX file ready for download.

---

### 10. **frontend/index.html** — UI
**What it does:**
- Dark theme, single-page app
- Two-panel upload (Employment Documents | Dispute Context)
- Chat input field (Phase 3)
- Displays red flags with severity badges (CRITICAL, SERIOUS, MODERATE, INFORMATIONAL)
- Sidebar: last 30 analyses
- Download button: generates DOCX report on-demand

**Key CSS variables:**
- `--bg: #1a1a1a` (dark background)
- `--red: #ef4444` (CRITICAL)
- `--orange: #f97316` (SERIOUS)
- `--yellow: #eab308` (MODERATE)
- `--text: #ececec` (light text for WCAG AA contrast)

---

### 11. **frontend/db.js** — Client-Side Session Storage
**What it does:**
- IndexedDB wrapper using `idb` library (Promise-based)
- Stores sessions: {id, created_at, title, contract_filenames, context_filenames, 
                    analysis, entity_map, verdict, chat_context, feedback}
- Functions: `saveSession()`, `getSession()`, `getAllSessions()`, `deleteSession()`
- **Server is stateless:** user content lives ONLY in browser IndexedDB

**Key exports:**
```javascript
export async function getDB()           // Get IndexedDB connection
export async function saveSession(session)
export async function getSession(id)
export async function getAllSessions()
export async function deleteSession(id)
```

---

## Redaction Pipeline (All Passes Before LLM)

```
Raw PDF Text
    ↓
Pass 1: Regex (Daytona + local fallback)
  • NRIC: S[0-9]{7}[A-Z]
  • Email: \w+@\w+\.\w+
  • Phone: +65 \d{4} \d{4}
  • Address patterns
  → [NRIC_1], [EMAIL_1], [PHONE_1], [ADDRESS_1]
    ↓
Pass 1.5: SG Company Suffixes (entity_map.py)
  • "Tech Corp Pte Ltd" → [ORG_1]
  → [ORG_1], [ORG_2], ...
    ↓
Pass 2: spaCy NER (en_core_web_sm)
  • PERSON: "Alice Wong" → [PERSON_1]
  • ORG: "Ministry of Manpower" → [ORG_2]
    ↓
RESULT: Fully redacted text ready for LLM
  • Entity Map saved (real → placeholder)
  • Entity Map returned to BROWSER (NEVER to LLM or Bright Data)
  • Browser uses it to de-redact DOCX report
```

---

## How Files Link Together

```
User Uploads Files
        ↓
index.html (frontend)
        ↓
main.py:analyze() endpoint
        ├→ security.py (validate_file)
        ├→ extractor.py (extract_text)
        ├→ entity_map.py (build_entity_map, apply_entity_map)
        ├→ redaction.py (redact_documents)
        │   └→ src/redactor.py (redact + fallback)
        ├→ scraper.py (get_regulations)
        ├→ analyzer.py (analyze_combined)
        │   └→ TokenRouter LLM API
        ├→ src/terminal3_signer.py (sign_report_hash)
        └→ JSON response
                ↓
        db.js (IndexedDB, frontend)
        saveSession()
                ↓
        Display results
        on browser
        
Optional: Download DOCX
        ↓
main.py:/api/download
        ├→ db.py (fetch saved analysis from IndexedDB via JS)
        ├→ entity_map (from IndexedDB)
        ├→ report_generator.py (generate_docx)
        │   └→ terminal3_signer.py (include signature)
        └→ FileResponse (DOCX bytes)
```

---

## Environment Variables (in .env)

```bash
TOKENROUTER_API_KEY=...      # OpenAI-compatible LLM router
DAYTONA_API_KEY=...          # Redaction sandbox
TERMINAL3_API_KEY=...        # HMAC signing
TERMINAL3_DID=...            # DID for attestation
BRIGHTDATA_API_KEY=...       # MOM regulation scraper
CLAUSEGUARD_MODEL=anthropic/claude-haiku-4.5  # LLM model (override)
CLAUSEGUARD_RATE_LIMIT=20/minute              # Per-IP rate limit
CLAUSEGUARD_SESSION_RATE_LIMIT=5              # Per-session token limit
CLAUSEGUARD_LLM_TIMEOUT=180                   # LLM timeout (seconds)
```

---

## Running the Application

### Start Backend
```bash
python3.13 -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

### Access Frontend
Open browser: `http://127.0.0.1:8000`

### Run Tests
```bash
python3.13 -m pytest tests/ -v
```

---

## Known Gotchas & Guardrails

### Python Version
- **ALWAYS use `python3.13`** (not bare `python3`, which is 3.14 empty)
- `python3.13 -m pip install pkg --break-system-packages`

### Database
- SQLite connection: `check_same_thread=False, timeout=10` (concurrent uvicorn safety)
- **NEVER use f-strings for SQL** — always parameterised queries

### PII & Redaction
1. All input is `<UNTRUSTED_DATA>` — wrap in markers before LLM
2. **All redaction passes BEFORE any text reaches LLM or Bright Data**
3. Entity map returned to BROWSER ONLY (de-redaction) — never sent to LLM
4. Daytona timeout: 45s/doc → fallback to local regex (always succeeds)

### Severity Tiers
- CRITICAL: red background, light text (#fecaca), WCAG AA (7.22:1 contrast)
- SERIOUS: orange
- MODERATE: yellow
- INFORMATIONAL: blue

### Downloads
- `/api/download` is **stateless** — processes input, returns DOCX, stores nothing
- De-redaction happens on-the-fly via entity_map

---

## Testing

**Test suite:** `tests/test_backend.py` (34 tests, 22-27 min)
```bash
python3.13 -m pytest tests/ -v
```

**Stress test:** `docs/STRESS_TEST.md` — 5 PDFs, max size, cross-doc contradictions

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      BROWSER (Frontend)                     │
│  index.html + db.js (IndexedDB, idb library, Phase 2+)      │
│  • Upload PDFs (contract + context)                         │
│  • Chat context input (Phase 3)                             │
│  • Display results, save sessions locally                   │
└────────────────────────────────┬────────────────────────────┘
                                 │ HTTP POST /api/analyze
                                 ↓
┌─────────────────────────────────────────────────────────────┐
│                    FASTAPI BACKEND (port 8000)              │
│                     (main.py orchestrator)                  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Input: contract_files, context_files, chat_context   │   │
│  └──────────────────────────────────────────────────────┘   │
│           ↓                                                 │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ 1. Validate (security.py) — size, count, extension   │   │
│  └──────────────────────────────────────────────────────┘   │
│           ↓                                                 │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ 2. Extract text (extractor.py, pdfplumber)           │   │
│  └──────────────────────────────────────────────────────┘   │
│           ↓                                                 │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ 3. Build entity map (entity_map.py, spaCy + regex)   │   │
│  │    → [PERSON_1], [ORG_1], [NRIC_1], [EMAIL_1]        │   │
│  └──────────────────────────────────────────────────────┘   │
│           ↓                                                 │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ 4. Redact (redaction.py → src/redactor.py, Daytona)  │   │
│  │    Concurrent per-doc, 45s timeout, local fallback   │   │
│  └──────────────────────────────────────────────────────┘   │
│           ↓                                                 │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ 5. Fetch regulations (scraper.py, Bright Data)       │   │
│  │    → ["Reg A (reference only)", "Reg B", "Reg C"]    │   │
│  └──────────────────────────────────────────────────────┘   │
│           ↓                                                 │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ 6. Analyze (analyzer.py → LLM)                       │   │
│  │    TokenRouter (claude-haiku-4.5 by default)         │   │
│  │    180s timeout, retry x4 on JSON parse error        │   │
│  │    → {red_flags[], verdict, recommendations}         │   │
│  └──────────────────────────────────────────────────────┘   │
│           ↓                                                 │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ 7. Sign (terminal3_signer.py, HMAC-SHA256)           │   │
│  │    Proves: unaltered (not: correct)                  │   │
│  └──────────────────────────────────────────────────────┘   │
│           ↓                                                 │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Output: {analysisArea, regulations, entity_map}      │   │
│  │         → returned to BROWSER                        │   │
│  └──────────────────────────────────────────────────────┘    │
└─────────────────────────────────┬────────────────────────────┘
                                 │ HTTP 200 + JSON
                                 ↓
┌─────────────────────────────────────────────────────────────┐
│                    BROWSER (Frontend)                       │
│  • IndexedDB saveSession()                                  │
│  • Display red flags, verdict, recommendations              │
│  • Show "Download DOCX" button                              │
└─────────────────────────────────┬────────────────────────────┘
                                 │ GET /api/download + entity_map
                                 ↓
┌─────────────────────────────────────────────────────────────┐
│                    FASTAPI BACKEND                          │
│  • report_generator.py → generate_docx()                    │
│  • De-redact using entity_map                               │
│  • Sign with Terminal 3                                     │
│  • Return DOCX bytes                                        │
└────────────────────────────────┬────────────────────────────┘
                                 │ FileResponse (DOCX)
                                 ↓
┌─────────────────────────────────────────────────────────────┐
│                 Browser Downloads .docx                     │
│                    (user's machine)                         │
└─────────────────────────────────────────────────────────────┘
```

---

## Summary: Read Files in This Order

1. **CLAUDE.md** — Understand guardrails & phase status
2. **backend/main.py** — Entry point, request flow
3. **backend/analyzer.py** — LLM calls, red flags
4. **backend/extractor.py** — PDF extraction
5. **backend/entity_map.py** — Cross-doc PII mapping
6. **backend/redaction.py** → **src/redactor.py** — Daytona redaction
7. **backend/db.py** — SQLite schema
8. **backend/security.py** — File validation
9. **backend/scraper.py** — Bright Data integration
10. **backend/report_generator.py** — DOCX generation
11. **frontend/index.html** — UI
12. **frontend/db.js** — Client-side storage
13. **tests/test_backend.py** — Unit tests

---

## Key Metrics

- **Total code:** 1,894 lines (backend + frontend)
- **Backend:** ~1,200 lines Python
- **Frontend:** ~700 lines JS/HTML
- **Test suite:** 34 tests, 22-27 minutes
- **LLM latency:** Haiku ~25s/doc, Sonnet ~47s/doc
- **File limits:** ≤10 files, ≤15MB/file, ≤50MB total
- **Rate limits:** 20 req/min per IP, 5 req/min per session token

---

## Common Tasks

### Add a new endpoint
1. Add route to `backend/main.py`
2. Call existing functions (analyzer, extractor, db, etc.)
3. Return JSON response

### Change the LLM model
```bash
export CLAUSEGUARD_MODEL=anthropic/claude-sonnet-4.6
python3.13 -m uvicorn backend.main:app --port 8000
```

### Adjust rate limits
```bash
export CLAUSEGUARD_RATE_LIMIT=50/minute
export CLAUSEGUARD_SESSION_RATE_LIMIT=10
```

### Understand a test failure
```bash
python3.13 -m pytest tests/test_backend.py::test_name -v -s
```

---

## Links & Resources

- **Entry command:** `python3.13 -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload`
- **Frontend:** `http://127.0.0.1:8000`
- **Database:** `data/data.db`
- **Tests:** `python3.13 -m pytest tests/ -v`
- **Stress test:** `docs/STRESS_TEST.md`
