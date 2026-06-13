"""
backend/main.py
ClauseGuard FastAPI backend.

Two-phase, confirmation-gated pipeline (no server-side session, nothing
persisted to disk -- the browser holds the redacted text between calls):

  POST /redact   multipart PDF -> extract text locally (pdfplumber)
                 -> redact PII in a Daytona sandbox
                 -> return {redacted_text, redaction_report, ...}
                 (Caller reviews the redacted text and explicitly confirms.)

  POST /analyze  JSON {redacted_text} -> analyze (Kimi/TokenRouter)
                 -> regulation_check (Bright Data, max 3 flags)
                 -> hash report (Daytona) -> sign hash (Terminal 3)
                 -> return the full assembled report.

The orchestration helpers (extract_text, run_redaction, run_analysis) are
importable and HTTP-free so the test harness can drive the whole pipeline
directly.

Run: python3.13 -m uvicorn backend.main:app --port 8000
"""

import io
import os
import sys

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Make `src` importable whether run as `backend.main` or from repo root.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()  # pull TOKENROUTER/DAYTONA/TERMINAL3/BRIGHTDATA keys from .env

import pdfplumber  # noqa: E402

from src.redactor import redact  # noqa: E402
from src.analyzer import analyze  # noqa: E402
from src.regulation_check import check_flags  # noqa: E402
from src.sandbox_validate import validate_and_hash  # noqa: E402
from src.terminal3_signer import sign_report_hash  # noqa: E402

# Minimum chars of extracted text before we trust the PDF isn't a scan.
MIN_TEXT_CHARS = 40

app = FastAPI(title="ClauseGuard")


# --------------------------------------------------------------------------
# Orchestration helpers (HTTP-free, importable, no disk persistence)
# --------------------------------------------------------------------------

def extract_text(pdf_bytes: bytes) -> str:
    """Extract text from a PDF held entirely in memory."""
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


def run_redaction(text: str) -> dict:
    """Redact PII in a sandbox. Returns redactor output + extracted_chars."""
    result = redact(text)
    result["extracted_chars"] = len(text)
    return result


def run_analysis(redacted_text: str) -> dict:
    """Analyze redacted text, fetch guidance, hash, and sign.

    Returns the full report dict the frontend renders.
    """
    report = analyze(redacted_text)

    flags = report.get("red_flags", [])
    guidance = check_flags(flags)

    # Fold guidance into the object we hash so the attestation covers
    # everything shown to the user.
    report_for_hash = dict(report)
    report_for_hash["regulation_guidance"] = guidance

    validation = validate_and_hash(report_for_hash)
    attestation = sign_report_hash(validation["report_hash"])

    return {
        "clause_summary": report.get("clause_summary", ""),
        "plain_english_summary": report.get("plain_english_summary", ""),
        "red_flags": flags,
        "regulation_guidance": guidance,
        "validation": validation,
        "attestation": attestation,
    }


# --------------------------------------------------------------------------
# HTTP endpoints
# --------------------------------------------------------------------------

class AnalyzeRequest(BaseModel):
    redacted_text: str


@app.post("/redact")
async def redact_endpoint(file: UploadFile = File(...)):
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a PDF file.")

    pdf_bytes = await file.read()
    try:
        text = extract_text(pdf_bytes)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read PDF: {e}")
    finally:
        del pdf_bytes  # do not retain the uploaded bytes

    if len(text.strip()) < MIN_TEXT_CHARS:
        raise HTTPException(
            status_code=422,
            detail="This looks like a scanned or image-only PDF -- text "
                   "extraction failed. ClauseGuard needs selectable text.",
        )

    try:
        return run_redaction(text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Redaction failed: {e}")


@app.post("/analyze")
async def analyze_endpoint(req: AnalyzeRequest):
    if len(req.redacted_text.strip()) < MIN_TEXT_CHARS:
        raise HTTPException(status_code=422, detail="No text to analyze.")
    try:
        return run_analysis(req.redacted_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")


# --------------------------------------------------------------------------
# Static frontend (served from ../frontend). Mounted last so it doesn't
# shadow the API routes.
# --------------------------------------------------------------------------

_FRONTEND_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend"
)


@app.get("/")
async def index():
    return FileResponse(os.path.join(_FRONTEND_DIR, "index.html"))


if os.path.isdir(_FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=_FRONTEND_DIR), name="static")
