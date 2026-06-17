# Claude Code Prompt — Known Issues Fix Sprint (Pre-v3)

Fix all fixable P1 issues before v3 work begins. This is a clean-up sprint, not a feature sprint. Read CLAUDE.md fully before writing a single line. Then read KNOWN_ISSUES.md.

---

## Pre-Mortem, Steelman, Red Team (read before starting)

**PRE-MORTEM:** ClauseGuard goes public on v3. A legal agency does a demo. Their accessibility reviewer opens DevTools and finds the CRITICAL severity badge is red-on-red (contrast ratio ~1:1 — invisible to anyone with red-green colour blindness). A mobile user on a 375px screen finds the sidebar occupies 70% of the screen. A transient 502 silently drops their analysis with no retry. These are the three failure modes most likely to surface in the first 48 hours of public use. All three are fixable today.

**STEELMAN:** Fixing P1s before v3 is not premature polish — it is the minimum bar for calling something a product rather than a prototype. Enterprise buyers and legal agencies will do due diligence. A WCAG failure on the most important UI element (CRITICAL severity badge) in a contract analysis tool is a credibility failure, not a minor cosmetic issue.

**RED TEAM:**

| Fix | Risk if done naively | Mitigation |
| --- | --- | --- |
| Badge contrast CSS | Changing severity badge colours may break dark theme elsewhere | Only change text colour — don’t touch background or border |
| Mobile responsive layout | Stacking panels vertically changes the UX flow; users may not see Panel B | Add clear label “Optional: Dispute Context ↓” when stacked |
| 4th retry for 502 | An extra retry means the analyze endpoint could take 4× LLM time | Only retry on JSON parse failure, NOT on timeout or network error |
| Eviction sweep for token dict | A background loop in FastAPI can cause threading issues | Use a lazy eviction approach (prune on each write, not in a loop) |
| Remove vestigial session_id | Clients that read session_id from the response will break | Check frontend for any reference to data.session_id before removing |

**HARD STOPS — do NOT touch these in this sprint:**

- NER single-word company names (presidio integration = new dependency + full re-verify)
- CORS=`*` (needs production domain first)
- Analysis latency (LLM-bound)
- Test suite duration (mocking changes what’s being tested)

---

## Pre-Flight

```bash
lsof -i :8000 | grep LISTEN | awk '{print $2}' | xargs kill 2>/dev/null; true
python3.13 -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 &
sleep 4 && curl -s http://127.0.0.1:8000/health
```

Expected: `{"status": "ok"}`. Report then continue.

---

## Fix 1 — CRITICAL Badge Contrast (WCAG AA)

**Problem:** CRITICAL severity badge is `rgb(239,68,68)` text on `rgba(239,68,68,0.25)` background. Same hue, contrast ratio ~1.3:1. WCAG AA requires 4.5:1 for normal text.

**Fix:** In `frontend/index.html`, find the severity badge CSS and update ONLY the text colours (do not change backgrounds):

```css
.severity-critical { color: #7f1d1d; }  /* dark red, contrast ~8:1 on translucent red bg */
.severity-serious  { color: #7c2d12; }  /* dark orange */
.severity-moderate { color: #713f12; }  /* dark amber */
.severity-informational { color: #1e3a5f; }  /* dark blue */
```

Verify via Chrome MCP:

```jsx
const el = document.querySelector('[class*="severity-critical"], .badge-critical, [data-severity="CRITICAL"]');
if (el) {
  const s = window.getComputedStyle(el);
  console.log('color:', s.color, 'bg:', s.backgroundColor);
}
```

If the selector returns null, inspect the DOM to find the actual severity class names being applied and adjust the CSS accordingly. Report the actual class names found and the computed colours after the fix.

---

## Fix 2 — Hide Download Button for INSUFFICIENT_INFORMATION

**Problem:** "Download Report" button appears even when the verdict is INSUFFICIENT_INFORMATION. The DOCX generates but the MOM letter section is empty — a confusing download for the user.

**Fix:** In `frontend/index.html`, in the `showDownloadButton()` function (or wherever `currentReport` is set and the button is shown), add a verdict check:

```jsx
function showDownloadButton(report) {
  const verdict = report?.judgment?.verdict;
  if (verdict === 'INSUFFICIENT_INFORMATION') {
    document.getElementById('download-report-btn').style.display = 'none';
    return;
  }
  document.getElementById('download-report-btn').style.display = 'block';
}
```

Also apply the same check in `loadSession()` when restoring a session.

Verify: run an analysis on `sample_data/synthetic_contract.pdf` with NO context files (Panel B empty). Verdict should be INSUFFICIENT_INFORMATION. Download button should NOT appear. Report.

---

## Fix 3 — STRESS_TEST.md Stale Element ID

**Problem:** STRESS_TEST.md Part A, Phase 5 tests (TEST P5-4 TEST A) checks `document.getElementById('results')`, but the real results container is `#analysisArea`.

**Fix:** Open `STRESS_TEST.md` and find the line:

```jsx
document.getElementById('results')?.getAttribute('role') // should be "status"
```

Replace with:

```jsx
document.getElementById('analysisArea')?.getAttribute('role') // should be "status"
```

Verify: `grep -n 'getElementById.*results' STRESS_TEST.md` should return no results after the fix (there should be no remaining references to `getElementById('results')`).

---

## Fix 4 — Remove Vestigial session_id from /api/analyze Response

**Problem:** The server still mints and returns a `session_id` in the `/api/analyze` response. Since Phase 2, sessions are client-generated (`crypto.randomUUID()`) and client-stored (IndexedDB). The server session_id is vestigial and misleading.

**First:** Check the frontend for any reference to `data.session_id` or `response.session_id`:

```bash
grep -n 'session_id' frontend/index.html
```

If any references exist, note them and update them before removing from the backend.

**Then:** In `backend/main.py`, find where `session_id` is added to the `/api/analyze` response JSON and remove it. The response should not include a server-generated session identifier.

Verify:

```bash
curl -s -X POST http://127.0.0.1:8000/api/analyze \
  -F "contract_files=@sample_data/synthetic_contract.pdf" | \
  python3.13 -c "import sys,json; d=json.load(sys.stdin); print('session_id present:', 'session_id' in d)"
```

Expected: `session_id present: False`. Report.

---

## Fix 5 — Tab Order (Sidebar DOM Reorder)

**Problem:** The sidebar is before the main content in the DOM, so tabbing through the page hits sidebar items (New Analysis, Clear my data, session entries) before the upload panels. Users tabbing through the main workflow (Panel A → Panel B → chat → Analyse) have to navigate through sidebar controls first.

**Fix:** Add `tabindex="-1"` to sidebar interactive elements that are not part of the primary workflow, so they’re reachable by click but not in the tab sequence. The main workflow elements keep their natural tab order:

```jsx
// Find sidebar buttons and session list items and set tabindex=-1
document.querySelectorAll('#sidebar button, #sidebar a, #session-list li').forEach(el => {
  el.setAttribute('tabindex', '-1');
});
```

Apply this in the `init()` function and whenever the session list is re-rendered.

Exceptions — these sidebar items SHOULD remain in tab order (set tabindex="0" explicitly):

- "Clear my data" button (accessibility-critical action)
- "Privacy Policy & Terms" link

Verify via Chrome MCP:

```jsx
const focusable = [...document.querySelectorAll('button:not([tabindex="-1"]), textarea:not([tabindex="-1"]), input:not([tabindex="-1"]), a:not([tabindex="-1"])')]
  .slice(0, 12)
  .map(el => el.tagName + ' ' + (el.id || el.textContent?.trim().slice(0,30)));
console.log(focusable);
```

Expected order: upload zone inputs, chat textarea, Analyse button, Clear my data, Privacy link. Sidebar session entries should NOT appear in this list. Report.

---

## Fix 6 — In-Memory Token Count Eviction (Lazy Sweep)

**Problem:** `_session_token_counts` in `backend/main.py` accumulates small timestamp lists per token indefinitely. Long uptime with many distinct tokens = slow memory leak.

**Fix:** Replace the current write with a lazy eviction — prune expired entries on each write, not in a background loop (avoids threading issues in FastAPI):

```python
def _check_session_rate(token: str, limit: int = 5, window: int = 60) -> bool:
    now = time.time()
    # Lazy eviction: clean up any token whose last request is older than window
    stale = [k for k, v in _session_token_counts.items()
             if not v or now - max(v) > window * 2]
    for k in stale:
        del _session_token_counts[k]
    # Check and update current token
    timestamps = [t for t in _session_token_counts.get(token, []) if now - t < window]
    if len(timestamps) >= limit:
        return False
    _session_token_counts[token] = timestamps + [now]
    return True
```

Verify:

```bash
# Simulate 100 distinct tokens, then check dict size
python3.13 -c "
import sys; sys.path.insert(0, '.')
from backend.main import _check_session_rate, _session_token_counts
import time
for i in range(100): _check_session_rate(f'token-{i}')
print('tokens tracked:', len(_session_token_counts))
# Simulate time passing (we can't sleep 120s, just verify eviction logic exists)
print('eviction logic present:', True)
"
```

Report dict size and confirm the eviction block is present in the function. P1 — not a hard requirement to test exhaustively.

---

## Fix 7 — 4th Retry for Transient 502 (Haiku JSON Failures)

**Problem:** `analyze_combined()` retries up to 3x on JSON parse/validation failure. The transient 502 rate is ~1-2 per 15 calls, occurring when Haiku returns malformed JSON even after 3 retries. A 4th retry would catch the remaining cases.

**Important constraint:** Only retry on JSON parse failure. Do NOT retry on timeout (that would make slow requests 4× slower) and do NOT retry on network errors.

**Fix:** In `backend/analyzer.py`, find the retry loop in `analyze_combined()` and change the max retries from 3 to 4:

```python
# Change
for attempt in range(3):
# To
for attempt in range(4):
```

Also check whether the fence-stripping logic handles all common malformed patterns:

- JSON wrapped in `json ...`  → should already be stripped
- JSON with a trailing comma before `}` → may not be handled
- JSON with a leading explanation before the `{` → should be handled by finding first `{`

If any of these patterns are not handled, add them to the fence-stripping step before retry.

Verify: `grep -n 'range(3\|range(4' backend/analyzer.py` should show `range(4)` in the retry loop. Report.

---

## Fix 8 — Mobile Responsive Layout (375px)

**Problem:** The sidebar is 256px fixed width. At 375px viewport, this leaves 119px for the main content area — too cramped for the upload panels, chat textarea, and analyse button.

**Fix:** Add a CSS media query that:

1. Collapses the sidebar to a top bar or hides it behind a toggle at < 640px
2. Stacks Panel A and Panel B vertically
3. Makes the Analyse button full-width

```css
@media (max-width: 640px) {
  #sidebar {
    width: 100%;
    height: auto;
    position: relative;
    border-right: none;
    border-bottom: 1px solid var(--border);
    padding: 0.5rem;
    display: flex;
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 0.5rem;
  }
  #session-list {
    display: none;  /* Hide session list on mobile — too cramped */
  }
  .panels-container {
    flex-direction: column;
  }
  .panel {
    width: 100%;
  }
  #analyse-btn {
    width: 100%;
  }
  body {
    flex-direction: column;
  }
}
```

If the actual class/ID names differ from above, read the DOM and apply to the correct selectors.

Verify via Chrome MCP — resize to 375px and check scrollWidth:

```jsx
window.innerWidth  // should be 375 if resize worked
document.documentElement.scrollWidth  // must equal or be less than 375
```

If Chrome MCP resize still can’t shrink the window, verify the CSS is applied by checking that `.panels-container` has `flex-direction: column` in the computed styles at narrow width:

```jsx
const panelContainer = document.querySelector('.panels-container, #panels-container, .upload-panels');
const mqTest = window.matchMedia('(max-width: 640px)');
console.log('media query matches:', mqTest.matches, '/ panels container:', panelContainer?.className);
```

Report: actual class names found, computed flex-direction, scrollWidth. If MCP can’t verify a true 375px render, log as P1 pending manual mobile test.

---

## Post-Fix: Run Full Regression Suite

After all 8 fixes, run the full automated test suite to confirm no regressions:

```bash
CLAUSEGUARD_TEST_BUDGET=180 python3.13 -m pytest tests/test_backend.py -v --tb=short 2>&1 | tail -20
```

Expected: 34/34 pass. Any new failure is a P0 — fix before moving on.

---

## Final Verification

1. CRITICAL badge is dark red text, contrast visibly improved (not red-on-red)
2. Analysis on contract-only (no context) — Download button does NOT appear
3. `grep -n 'getElementById.*results' STRESS_TEST.md` returns 0 results
4. `/api/analyze` response JSON does NOT contain `session_id` key
5. Tab order: upload panels appear before sidebar session entries in focusable sequence
6. `_check_session_rate` function contains eviction logic
7. `analyze_combined()` uses `range(4)` not `range(3)`
8. `@media (max-width: 640px)` block exists in `frontend/index.html`
9. 34/34 automated tests pass

Report all 9 checks pass/fail. Log any new P1s in KNOWN_ISSUES.md. Stop after final verification — do not start v3 work without being asked.

Per CLAUDE.md: stop after each fix and report before continuing. Use `python3.13` explicitly.