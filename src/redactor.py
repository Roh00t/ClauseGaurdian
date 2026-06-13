"""
src/redactor.py
Daytona sandbox: regex-based PII redaction of extracted contract text.
Stdlib only (re, json) -- no extra installs needed in the sandbox image,
same proven pattern as sandbox_validate.py.

Redacts (best-effort): Singapore NRIC/FIN numbers, email addresses,
Singapore phone numbers, and common residential-address patterns
(unit numbers, blocks, 6-digit postal codes).

Returns {redacted_text, redaction_report}. The redaction_report lists
WHAT TYPES were redacted and HOW MANY of each -- it never echoes the
original PII values back out of the sandbox.

IMPORTANT: the contract text is NOT embedded in the script source -- it
is uploaded to the sandbox as a file (sandbox.fs.upload_file) and read
back inside the script. This avoids any source-escaping fragility (the
redaction regexes already contain brace quantifiers like \\d{7} and
{2,}, and contract text can contain arbitrary quotes/backslashes).
"""

import os
import json
from daytona import Daytona, DaytonaConfig


# Reads the uploaded contract text from /tmp and emits a JSON result.
REDACTION_SCRIPT = r'''
import re, json

with open("/tmp/contract.txt", "r", encoding="utf-8") as f:
    text = f.read()

# Order matters: emails first (their local part can contain digit runs that
# would otherwise look like phone numbers), then NRIC, phone, address.
PATTERNS = [
    # Singapore NRIC / FIN: [STFG] + 7 digits + checksum letter.
    ("NRIC", re.compile(r"\b[STFGstfg]\d{7}[A-Za-z]\b")),
    # Email addresses.
    ("EMAIL", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    # Singapore phone numbers: optional +65, then an 8-digit number starting
    # 3/6/8/9, allowing a space or hyphen in the middle (9123 4567).
    ("PHONE", re.compile(r"(?<!\d)(?:\+?65[\s-]?)?[3689]\d{3}[\s-]?\d{4}(?!\d)")),
    # Address fragments: unit numbers (#12-345), block numbers (Blk/Block 123),
    # and 6-digit Singapore postal codes (often preceded by "Singapore").
    ("ADDRESS", re.compile(
        r"#\d{1,3}-\d{1,4}[A-Za-z]?"
        r"|\b(?:Blk|Block)\s+\d{1,4}[A-Za-z]?\b"
        r"|\bSingapore\s+\d{6}\b"
        r"|(?<!\d)\d{6}(?!\d)",
        re.IGNORECASE,
    )),
]

redaction_report = {}
for label, pattern in PATTERNS:
    text, count = pattern.subn("[REDACTED_%s]" % label, text)
    if count:
        redaction_report[label] = count

result = {
    "redacted_text": text,
    "redaction_report": redaction_report,
    "total_redactions": sum(redaction_report.values()),
}
print(json.dumps(result))
'''


def redact(contract_text: str) -> dict:
    """Run regex PII redaction inside a Daytona sandbox.

    Returns {redacted_text, redaction_report, total_redactions}.
    """
    api_key = os.environ.get("DAYTONA_API_KEY")
    if not api_key:
        raise RuntimeError("DAYTONA_API_KEY is not set")

    daytona = Daytona(DaytonaConfig(api_key=api_key))
    sandbox = daytona.create()

    try:
        # Upload the contract text as a file rather than embedding it in the
        # script source -- see module docstring.
        sandbox.fs.upload_file(contract_text.encode("utf-8"), "/tmp/contract.txt")

        run = sandbox.process.code_run(REDACTION_SCRIPT)
        if run.exit_code != 0:
            raise RuntimeError(f"Sandbox redaction failed: {run.result}")

        return json.loads(run.result.strip())
    finally:
        sandbox.delete()


if __name__ == "__main__":
    import pdfplumber

    # 1) Real run against the synthetic contract's extracted text.
    with pdfplumber.open("sample_data/synthetic_contract.pdf") as pdf:
        contract = "\n".join(p.extract_text() or "" for p in pdf.pages)

    print("=== Synthetic contract ===")
    out = redact(contract)
    print("redaction_report:", json.dumps(out["redaction_report"]))
    print("total_redactions:", out["total_redactions"])

    # 2) Mechanism check: inject one of each PII type and confirm each
    #    pattern fires and that no original value leaks into the report.
    probe = (
        "Employee NRIC: S1234567A. Contact: alex.tan@example.com or +65 9123 4567. "
        "Address: Blk 123 Clementi Ave 3 #12-345 Singapore 120123. "
        "Office line 6789 0123. Monthly salary S$3,000.00 paid on the 1st."
    )
    print("\n=== PII probe ===")
    out2 = redact(probe)
    print("redaction_report:", json.dumps(out2["redaction_report"]))
    print("redacted_text:", out2["redacted_text"])
    # Salary/date must survive; PII must be gone.
    leaked = [v for v in ["S1234567A", "alex.tan@example.com", "9123 4567", "120123"]
              if v in out2["redacted_text"]]
    print("LEAKED (should be []):", leaked)
    print("salary preserved:", "S$3,000.00" in out2["redacted_text"])
