"""
backend/supabase_client.py — v3 Supabase integration (service-role only).

Guardrail #13: stores METADATA ONLY — user_id, tier, timestamps, mode,
verdict_category. NEVER contract text, analysis JSON, or entity map values.
Guardrail #14: anonymous requests are never blocked here; only logged-in
requests are subject to the analyses_used cap.
"""
import os
from dotenv import load_dotenv

load_dotenv()

_SUPABASE_URL = os.getenv("SUPABASE_URL", "")
_SERVICE_KEY = os.getenv("SUPABASE_SECRET_KEY", "")

FREE_ANALYSIS_LIMIT = 3  # logged-in free-tier cap (paid = uncapped)


def _client():
    from supabase import create_client
    return create_client(_SUPABASE_URL, _SERVICE_KEY)


def verify_user_token(token: str) -> dict | None:
    """Validate a Supabase JWT using the auth admin API. Returns {user_id, email} or None."""
    if not token:
        return None
    try:
        c = _client()
        resp = c.auth.get_user(token)
        if resp and resp.user:
            return {"user_id": str(resp.user.id), "email": resp.user.email or ""}
    except Exception:
        pass
    return None


def get_user_profile(user_id: str) -> dict | None:
    """Return the user_profiles row for this user, or None if not found."""
    try:
        r = _client().table("user_profiles").select("tier,analyses_used").eq("user_id", user_id).single().execute()
        return r.data
    except Exception:
        return None


def increment_analyses_used(user_id: str) -> None:
    """Increment analyses_used for a logged-in user. Failure never blocks analysis."""
    try:
        c = _client()
        row = c.table("user_profiles").select("analyses_used").eq("user_id", user_id).single().execute()
        current = (row.data or {}).get("analyses_used", 0)
        c.table("user_profiles").update({"analyses_used": current + 1}).eq("user_id", user_id).execute()
    except Exception:
        pass


def log_analysis_metadata(user_id: str, mode: str, verdict_category: str | None, docs_count: int) -> None:
    """Insert one analysis_metadata row. Metadata only — guardrail #13."""
    try:
        _client().table("analysis_metadata").insert({
            "user_id": user_id,
            "mode": mode,
            "verdict_category": verdict_category,
            "docs_count": docs_count,
        }).execute()
    except Exception:
        pass
