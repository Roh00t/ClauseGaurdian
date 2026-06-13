"""
Test configuration. Imported by pytest BEFORE the test modules, so the env
vars set here are in place before backend.main reads them at import time.

We raise the analyze rate limit (prod default 5/min) out of the way so the
stress suite, which fires ~20 analyze calls in seconds, isn't throttled. The
production 5/min limit is verified separately (manual curl loop / Part B).
"""
import os

os.environ.setdefault("CLAUSEGUARD_RATE_LIMIT", "100000/minute")
