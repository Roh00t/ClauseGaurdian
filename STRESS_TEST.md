---

## PHASE 5 — PRODUCTION READINESS TESTS

### TEST P5-1 — Terms of Service / Privacy Policy
Navigate to http://127.0.0.1:8000/tos

Page loads without error (not 404)?
Contains "processes per-request, retains nothing"?
Contains "TokenRouter" and "Bright Data" named as third parties?
Contains "IndexedDB" or "your browser's local storage"?
Contains "not legal advice"?
Footer link on index.html: "Privacy Policy & Terms" links to /tos?

Check that it does NOT say "we never see your data" (inaccurate — server

processes per-request). Report pass/fail. Flag as P0 if any of items 2-6 fail.

### TEST P5-2 — Rate Limiting
With server running on http://127.0.0.1:8000:
TEST A — Per-IP limit (20/min):

Run 22 rapid requests without a session token:

for i in {1..22}; do curl -s -o /dev/null -w "%{http_code}\n" 

-X POST http://127.0.0.1:8000/api/analyze; done | tail -5

Expected: 429 appears at or before request 21.
TEST B — Per-session-token limit (5/min):

Run 7 requests with the same token:

for i in {1..7}; do curl -s -o /dev/null -w "%{http_code}\n" 

-H "X-Session-Token: stress-test-token-abc" 

-X POST http://127.0.0.1:8000/api/analyze; done | tail -3

Expected: 429 appears at or before request 6.
TEST C — Different tokens not shared:

Two rapid requests with different tokens — both should succeed (not 429):

curl -s -o /dev/null -w "%{http_code}\n" 

-H "X-Session-Token: token-aaa" -X POST http://127.0.0.1:8000/api/analyze

curl -s -o /dev/null -w "%{http_code}\n" 

-H "X-Session-Token: token-bbb" -X POST http://127.0.0.1:8000/api/analyze

Expected: both return 400/422 (no files) NOT 429.
Report: all three pass/fail.

### TEST P5-3 — Feedback Mechanism
On http://127.0.0.1:8000:

Run analysis on synthetic_contract.pdf.
Do 👍 and 👎 buttons appear on each red flag card?
Click 👍 on the first red flag. Does a "Marked accurate" note appear?
Hard-refresh (Cmd+Shift+R). Click the session in sidebar.
Does the first red flag still show "Marked accurate" (persisted in IndexedDB)?
Check browser dev tools: Application > IndexedDB > clauseguard > sessions >

entry. Does it have a "feedback" field with an entry for flag 0?
Click "Clear my data". Does the feedback clear along with everything else?

Report: pass/fail per step. P0 if feedback doesn't persist (step 5).

### TEST P5-4 — Accessibility
On http://127.0.0.1:8000:
TEST A — ARIA live regions:

Open dev tools. Run in console:

document.getElementById('analysisArea')?.getAttribute('role') // should be "status"

document.getElementById('analysisArea')?.getAttribute('aria-live') // should be "polite"

Expected: "status" and "polite". P0 if absent.
TEST B — Keyboard navigation (tab through interactive elements):

Press Tab repeatedly from the top of the page. Can you reach:

"New Analysis" button?
Panel A upload zone?
Panel B upload zone?
Chat textarea?
"Analyse Everything" button?
"Clear my data" button?

Report which elements are NOT reachable by tab (P0 if Analyse button not reachable).

TEST C — Mobile viewport (375px):

window.resizeTo(375, 812);

document.documentElement.scrollWidth > 375  // true = horizontal scroll = P0

Does layout stack vertically (panels one above the other rather than side by side)?

Is the Analyse button visible without horizontal scroll?

Report: scroll width and whether layout adapts.

### TEST P5-5 — Multi-Language
On http://127.0.0.1:8000:

Find the language selector (EN/MS/TL) in the top bar. Is it present?
Switch to MS (Malay). Does the disclaimer text change to Malay?
Switch to TL (Tagalog). Does the disclaimer text change to Tagalog?
Does the Tagalog MOM letter note include a stronger warning about

legal translation? (Should contain "legal na pagsasalin" or similar)
Hard-refresh. Is the language preference preserved (localStorage)?
Switch back to EN. Disclaimer reverts to English?

Report: pass/fail per step.

### PHASE 5 FINAL CHECKLIST

- [ ] `/tos` loads and contains "processes per-request, retains nothing"
- [ ] Rate limit 429 fires after 20 IP requests / 5 same-token requests
- [ ] Feedback thumbs persist in IndexedDB and reload on session click
- [ ] `results` div has `role=status` and `aria-live=polite`
- [ ] All 6 interactive elements reachable by tab
- [ ] No horizontal scroll at 375px mobile viewport
- [ ] Language selector switches disclaimer text and persists on reload
- [ ] No P0 issues from any Phase 5 test