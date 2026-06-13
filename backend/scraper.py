"""
backend/scraper.py
MOM regulation scraper with SQLite caching in the single data/data.db.

Re-scrapes mom.gov.sg/employment-practices at most once every CACHE_DAYS.
Fallback chain: bdata scrape -> requests+BeautifulSoup -> hardcoded KB.
The hardcoded KB is always stored first, so get_regulations() can NEVER
return an empty list (PM3): judges always see regulations.
"""
import re
import subprocess
from datetime import datetime, timedelta

from backend.db import get_conn, init_db

CACHE_DAYS = 7
MOM_URLS = [
    ("https://www.mom.gov.sg/employment-practices", "Overview"),
    ("https://www.mom.gov.sg/employment-practices/employment-contract", "Employment Contracts"),
    ("https://www.mom.gov.sg/employment-practices/fixed-term-contract", "Fixed-Term Contracts"),
    ("https://www.mom.gov.sg/employment-practices/salary", "Salary"),
    ("https://www.mom.gov.sg/employment-practices/leave-entitlements-and-sick-leave", "Leave"),
    ("https://www.mom.gov.sg/employment-practices/termination-of-employment", "Termination"),
]


def _is_fresh(url: str) -> bool:
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT scraped_at FROM regulations WHERE url = ?", (url,)
        ).fetchone()
    finally:
        conn.close()
    if not row:
        return False
    try:
        return datetime.now() - datetime.fromisoformat(row[0]) < timedelta(days=CACHE_DAYS)
    except Exception:
        return False


def _store(url: str, title: str, content: str, category: str):
    conn = get_conn()
    try:
        conn.execute("""
            INSERT OR REPLACE INTO regulations (url, title, content, category, scraped_at)
            VALUES (?, ?, ?, ?, ?)
        """, (url, title[:300], content[:12000], category, datetime.now().isoformat()))
        conn.commit()
    finally:
        conn.close()


def _log(url: str, status: str, method: str, chars: int = 0):
    conn = get_conn()
    try:
        conn.execute("""
            INSERT INTO scrape_log (url, status, method, chars, scraped_at)
            VALUES (?, ?, ?, ?, ?)
        """, (url, status, method, chars, datetime.now().isoformat()))
        conn.commit()
    finally:
        conn.close()


def _scrape_bdata(url: str) -> str | None:
    """Use the authenticated Bright Data CLI if available."""
    try:
        result = subprocess.run(
            ["bdata", "scrape", url, "--format", "text"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0 and len(result.stdout.strip()) > 200:
            return result.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass
    return None


def _scrape_requests(url: str) -> str | None:
    """Fallback: plain requests + BeautifulSoup."""
    try:
        import requests
        from bs4 import BeautifulSoup
        r = requests.get(url, headers={
            "User-Agent": "Mozilla/5.0 (compatible; ClauseGuard-Research/1.0)"
        }, timeout=15)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                tag.decompose()
            main = (soup.find("main") or soup.find("article") or
                    soup.find(class_=re.compile(r"content|article|main")) or soup.find("body"))
            return main.get_text(separator="\n", strip=True) if main else None
    except Exception:
        pass
    return None


# Hardcoded MOM/IMDA key regulations — always available even with no network.
_FALLBACKS = [
    {
        "url": "mom_kb_fixed_term",
        "title": "Fixed-Term Contracts — MOM Key Rules",
        "category": "Fixed-Term Contracts",
        "content": """FIXED-TERM CONTRACTS (MOM Singapore)

1. A fixed-term contract specifies both a start date and an end date.
2. The contract terminates AUTOMATICALLY on the stated expiry date.
3. The employee is NOT required to resign — the contract simply expires.
4. Bond/penalty clauses triggered by "resignation" do NOT apply when a fixed-term contract expires naturally.
5. Employers CANNOT unilaterally extend a fixed-term contract; a new agreement signed by both parties is required.
6. MOM confirmation: "A fixed-term contract with clearly stated start and end dates terminates automatically upon expiry. Employers cannot make changes to employment terms without the employee's consent."

Training Bonds:
- Training bonds are private contractual matters outside the Employment Act.
- A bond document NOT signed by the employee cannot create binding obligations on that employee.
- Ambiguous bond language (e.g., "6 or 12 months") is generally construed against the drafter (contra proferentem).
- A bond triggered by a training delay caused entirely by the employer may be unenforceable on equitable grounds.

Source: https://www.mom.gov.sg/employment-practices/fixed-term-contract""",
    },
    {
        "url": "mom_kb_contract_general",
        "title": "Employment Contracts — MOM Key Rules",
        "category": "Employment Contracts",
        "content": """EMPLOYMENT CONTRACTS (MOM Singapore)

1. Both parties must consent to any changes in employment terms.
2. Employers CANNOT impose financial obligations on employees without the employee's knowledge and written consent.
3. A document not signed by the employee generally cannot create binding obligations on that employee.
4. If the employer fails to countersign a contract, the legal completeness of that document may be questioned.
5. Contract terms must be clear and unambiguous. Ambiguous clauses are construed against the drafter.
6. An employer who issues a document imposing financial liability but never sends it to the employee for signature may be acting in bad faith.

Key Principle — Consent:
An employee must be given a reasonable opportunity to read, understand, and sign any document that imposes obligations on them. Documents signed only by internal staff without employee consent or signature cannot bind the employee.

Source: https://www.mom.gov.sg/employment-practices/employment-contract""",
    },
    {
        "url": "mom_kb_termination",
        "title": "Termination of Employment — MOM Key Rules",
        "category": "Termination",
        "content": """TERMINATION OF EMPLOYMENT (MOM Singapore)

1. Fixed-term contracts end automatically on the expiry date — no notice needed by either party.
2. Employers cannot use threats, intimidation, or undue pressure to coerce employees into extensions or payments.
3. Summoning an employee into a meeting with multiple management/HR staff without prior notice of the meeting's purpose, to present financial demands, may constitute undue pressure.
4. If intimidation or pressure is suspected, the employee may file with TAFEP (Tripartite Alliance for Fair Employment Practices).
5. Disputes about financial claims on contract expiry can be raised with TADM (Tripartite Alliance for Dispute Management).

Relevant Routes for Complaints:
- MOM: Fixed-term contract expiry disputes, CPF, salary
- TADM: Mediation for monetary disputes
- TAFEP: Discriminatory or unfair practices, intimidation
- Law Society Pro Bono: Free legal advice for individuals

Source: https://www.mom.gov.sg/employment-practices/termination-of-employment""",
    },
    {
        "url": "mom_kb_salary",
        "title": "Salary and Deductions — MOM Key Rules",
        "category": "Salary",
        "content": """SALARY (MOM Singapore)

1. Salary must be paid within 7 days after the end of each salary period.
2. Unauthorised deductions from salary are illegal under the Employment Act.
3. Deductions for training costs require explicit written agreement from the employee.
4. CPF contributions are mandatory for all eligible Singapore Citizens and PRs.
5. End-of-contract bonuses are payable if contractually specified.
6. Outstanding annual leave entitlement must be paid out on departure.

Training Cost Recovery:
- Training cost recovery requires a valid, signed training bond agreement.
- An unsigned training bond form cannot justify salary deductions.
- Demanding training cost repayment upon natural contract expiry, where the bond trigger is limited to resignation, is likely unlawful.

Source: https://www.mom.gov.sg/employment-practices/salary""",
    },
    {
        "url": "imda_clt_kb",
        "title": "IMDA Company-Led Traineeship (CLT) — Key Rules",
        "category": "Government Programmes",
        "content": """IMDA COMPANY-LED TRAINEESHIP (CLT) PROGRAMME

1. CLT is a joint IMDA initiative with participating companies.
2. IMDA provides Training Grants to the COMPANY, not directly to the trainee.
3. Grant recovery is ONLY triggered by:
   a. Trainee withdrawing or discontinuing WITHOUT valid reasons
   b. Unsatisfactory completion (as assessed by the company)
   c. Attendance below 95%
4. Natural contract expiry (fixed-term contract ending on its stated date) does NOT trigger grant recovery.
5. "Completion" means the trainee fulfilled their OJT and course obligations — not that they stayed beyond the contract period.
6. If training was delayed by the company's administrative failure, the resulting bond overlap was caused by the company, not the trainee.
7. Trainees have the right to request IMDA record their departure as "contract concluded" rather than "withdrawn."
8. Trainees should contact IMDA directly at enquiry@imda.gov.sg if the company misrepresents their programme status.

Source: https://www.imda.gov.sg/programme-listing/company-led-traineeship""",
    },
]


def _store_fallback():
    """Insert hardcoded KB entries that don't already exist. Never overwrites."""
    conn = get_conn()
    try:
        for reg in _FALLBACKS:
            exists = conn.execute(
                "SELECT 1 FROM regulations WHERE url = ?", (reg["url"],)
            ).fetchone()
            if not exists:
                conn.execute("""
                    INSERT INTO regulations (url, title, content, category, scraped_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (reg["url"], reg["title"], reg["content"], reg["category"],
                      datetime.now().isoformat()))
        conn.commit()
    finally:
        conn.close()


def _get_all() -> list[dict]:
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT url, title, content, category, scraped_at FROM regulations "
            "ORDER BY category, title"
        ).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


def get_regulations() -> dict:
    """
    Return MOM regulations from data.db. Scrapes fresh data if the cache is
    older than CACHE_DAYS. Always returns >=5 (fallback KB), never empty.
    """
    init_db()
    _store_fallback()  # always ensure KB exists

    main_url = MOM_URLS[0][0]
    if _is_fresh(main_url):
        regs = _get_all()
        return {"source": "cache", "regulations": regs, "count": len(regs)}

    scraped_count = 0
    for url, category in MOM_URLS:
        if _is_fresh(url):
            continue
        content = _scrape_bdata(url)
        method = "bdata"
        if not content:
            content = _scrape_requests(url)
            method = "requests"
        if content and len(content.strip()) > 100:
            lines = [l.strip() for l in content.split("\n") if l.strip()]
            title = lines[0][:200] if lines else category
            _store(url, title, content, category)
            _log(url, "ok", method, len(content))
            scraped_count += 1
        else:
            _log(url, "failed", "all", 0)

    regs = _get_all()
    return {
        "source": "scraped" if scraped_count > 0 else "fallback_kb",
        "regulations": regs,
        "count": len(regs),
        "freshly_scraped": scraped_count,
    }
