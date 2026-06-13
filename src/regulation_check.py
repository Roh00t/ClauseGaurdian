"""
src/regulation_check.py
Bright Data `bdata search` wrapper for surfacing live, related regulatory
guidance for red flags tagged regulation_lookup=true.

Called per regulation-tagged flag, capped at MAX_FLAGS (default 3) flags
total to stay within the time/quota budget. Results are LABELLED as
"related guidance -- verify relevance", never as proof: Bright Data is a
web search, not a legal authority.

Regulation lookup is best-effort and NON-CRITICAL: if `bdata` is missing,
times out, or returns malformed data, this returns an empty result for
that flag and the pipeline continues. It must never crash the analysis.
"""

import json
import shutil
import subprocess

MAX_FLAGS = 3            # cap total flags we look up
NUM_PER_FLAG = 3         # organic results kept per flag
SEARCH_TIMEOUT = 60      # seconds per bdata call

GUIDANCE_LABEL = "related guidance -- verify relevance (not legal proof)"


def search_guidance(query: str, num: int = NUM_PER_FLAG) -> list:
    """Run one `bdata search` and return up to `num` organic results.

    Each result is {title, link, source, description}. Returns [] on any
    failure (missing CLI, timeout, bad JSON, non-zero exit).
    """
    if shutil.which("bdata") is None:
        return []

    try:
        proc = subprocess.run(
            ["bdata", "search", query, "--country", "sg", "--json"],
            capture_output=True,
            text=True,
            timeout=SEARCH_TIMEOUT,
        )
    except (subprocess.TimeoutExpired, OSError):
        return []

    if proc.returncode != 0 or not proc.stdout.strip():
        return []

    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return []

    organic = data.get("organic") or []
    results = []
    for item in organic[:num]:
        results.append({
            "title": item.get("title", ""),
            "link": item.get("link", ""),
            "source": item.get("source") or item.get("display_link", ""),
            "description": (item.get("description") or "")[:300],
        })
    return results


def _build_query(flag: dict) -> str:
    """Construct a focused Singapore-employment-law search query for a flag."""
    clause = (flag.get("clause") or "").strip()
    issue = (flag.get("issue") or "").strip()
    seed = clause or issue
    # Keep it short; prefix with jurisdiction + authority for relevance.
    return f"Singapore employment law MOM {seed}"[:200]


def check_flags(flags: list, max_flags: int = MAX_FLAGS) -> list:
    """Look up related guidance for regulation-tagged flags.

    Returns a list (one entry per looked-up flag):
      {flag_index, clause, query, label, results: [...]}
    Only flags with truthy regulation_lookup are considered, capped at
    max_flags. Order is preserved.
    """
    out = []
    looked_up = 0
    for idx, flag in enumerate(flags):
        if looked_up >= max_flags:
            break
        if not flag.get("regulation_lookup"):
            continue

        query = _build_query(flag)
        results = search_guidance(query)
        out.append({
            "flag_index": idx,
            "clause": flag.get("clause", ""),
            "query": query,
            "label": GUIDANCE_LABEL,
            "results": results,
        })
        looked_up += 1
    return out


if __name__ == "__main__":
    sample_flags = [
        {
            "clause": "Program Bond of 6- or 12-months",
            "issue": "Ambiguous bond duration on a fixed-term contract.",
            "severity": "serious",
            "regulation_lookup": True,
        },
        {
            "clause": "Company may terminate by giving 3 days' notice",
            "issue": "Asymmetric notice period.",
            "severity": "serious",
            "regulation_lookup": False,
        },
    ]
    out = check_flags(sample_flags)
    print(json.dumps(out, indent=2))
