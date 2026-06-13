"""
src/terminal3_signer.py
Signs the sandbox-computed report hash using the Terminal 3 API key/DID
as an HMAC signing secret. Pure stdlib -- no network call, can't fail
due to connectivity.
"""

import os
import hmac
import hashlib
import time


def sign_report_hash(report_hash: str) -> dict:
    api_key = os.environ.get("TERMINAL3_API_KEY")
    did = os.environ.get("TERMINAL3_DID")
    if not api_key or not did:
        raise RuntimeError("TERMINAL3_API_KEY / TERMINAL3_DID not set")

    signature = hmac.new(
        api_key.encode("utf-8"), report_hash.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    return {
        "did": did,
        "report_hash": report_hash,
        "signature": signature,
        "signed_at": time.time(),
    }


if __name__ == "__main__":
    print(sign_report_hash("0" * 64))