"""
src/sandbox_validate.py
Daytona sandbox: structural validation + hashing of the analyzer's JSON
report. Stdlib only (json, hashlib) -- proven to work with no extra
installs in the sandbox.
"""

import os
import json
from daytona import Daytona, DaytonaConfig


VALIDATION_SCRIPT_TEMPLATE = """
import json, hashlib

report = json.loads('''{report_json}''')

flags = report.get("red_flags", [])
required_keys = {{"clause", "issue", "severity", "regulation_lookup"}}

structurally_valid = all(required_keys.issubset(f.keys()) for f in flags)
severity_counts = {{}}
for f in flags:
    sev = f.get("severity", "unknown")
    severity_counts[sev] = severity_counts.get(sev, 0) + 1

report_bytes = json.dumps(report, sort_keys=True).encode("utf-8")
report_hash = hashlib.sha256(report_bytes).hexdigest()

result = {{
    "structurally_valid": structurally_valid,
    "num_red_flags": len(flags),
    "severity_counts": severity_counts,
    "report_hash": report_hash,
}}
print(json.dumps(result))
"""


def validate_and_hash(report: dict) -> dict:
    api_key = os.environ.get("DAYTONA_API_KEY")
    if not api_key:
        raise RuntimeError("DAYTONA_API_KEY is not set")

    daytona = Daytona(DaytonaConfig(api_key=api_key))
    sandbox = daytona.create()

    try:
        report_json = json.dumps(report)
        script = VALIDATION_SCRIPT_TEMPLATE.format(report_json=report_json)

        result = sandbox.process.code_run(script)
        if result.exit_code != 0:
            raise RuntimeError(f"Sandbox validation failed: {result.result}")

        return json.loads(result.result.strip())
    finally:
        sandbox.delete()


if __name__ == "__main__":
    sample_report = {
        "clause_summary": "test",
        "plain_english_summary": "test",
        "red_flags": [
            {"clause": "x", "issue": "y", "severity": "serious", "regulation_lookup": True}
        ],
    }
    print(json.dumps(validate_and_hash(sample_report), indent=2))