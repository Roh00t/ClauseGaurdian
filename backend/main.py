"""
backend/main.py — ClauseGuard v2 FastAPI app.

Routes:
  GET  /                     -> serves the single-page frontend
  GET  /health               -> {"status":"ok"}
  GET  /api/regulations      -> MOM regulation cache status (no full content)
  POST /api/analyze          -> multi-PDF upload -> red-flag analysis JSON
  GET  /api/sessions         -> last 30 analyses (sidebar)
  GET  /api/session/{id}     -> one saved analysis

Run from the repo root (note the package path — backend/__init__.py must exist):
  python3.13 -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
"""
import os
import sys
import json
import uuid
from datetime import datetime
from pathlib import Path

# Make `backend` importable when uvicorn is launched from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

load_dotenv()

from backend.db import get_conn, init_db
from backend.scraper import get_regulations
from backend.extractor import extract_text
from backend.analyzer import analyze_documents
from backend.security import validate_file, MAX_FILES, MAX_TOTAL_SIZE_BYTES

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

# ── App + rate limiting (RT4) ────────────────────────────────────────────────
# Configurable so the automated stress suite (which fires many analyze calls in
# seconds) can raise it; production default is 5/minute per IP.
RATE_LIMIT = os.getenv("CLAUSEGUARD_RATE_LIMIT", "5/minute")
limiter = Limiter(key_func=get_remote_address, default_limits=[])
app = FastAPI(title="ClauseGuard", version="2.0")
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def _rate_limit_handler(request: Request, exc: RateLimitExceeded):
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests — please wait a minute and try again."},
    )


app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def _startup():
    init_db()


# ── Static frontend ──────────────────────────────────────────────────────────
@app.get("/")
async def root():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/health")
async def health():
    return {"status": "ok", "ts": datetime.now().isoformat()}


# ── Regulations ──────────────────────────────────────────────────────────────
@app.get("/api/regulations")
async def regulations():
    """MOM regulation cache status. Full content is stripped (LLM-only)."""
    try:
        result = get_regulations()
        for r in result.get("regulations", []):
            r.pop("content", None)
        return result
    except Exception as e:
        raise HTTPException(500, detail=str(e))


# ── Analyze ──────────────────────────────────────────────────────────────────
@app.post("/api/analyze")
@limiter.limit(RATE_LIMIT)
async def analyze(request: Request, files: list[UploadFile] = File(...)):
    """Accept up to 10 PDFs, validate, extract, run LLM analysis, persist."""
    if not files:
        raise HTTPException(400, "No files provided.")
    if len(files) > MAX_FILES:
        raise HTTPException(400, f"Too many files — maximum {MAX_FILES} per request.")

    # 1. Read + validate every file (extension, magic bytes, size). RT1/RT2.
    documents = []
    errors = []
    total_bytes = 0
    for f in files:
        raw = await f.read()
        total_bytes += len(raw)
        if total_bytes > MAX_TOTAL_SIZE_BYTES:
            raise HTTPException(413, "Total upload exceeds 50MB limit.")
        validate_file(f.filename, raw)  # raises HTTPException on violation
        result = extract_text(raw, f.filename)
        if result["success"]:
            documents.append({"filename": f.filename, "text": result["text"]})
        else:
            errors.append({"filename": f.filename, "error": result["error"]})

    if not documents:
        raise HTTPException(422, detail={
            "message": "No text could be extracted from any uploaded file. "
                       "Image-only/scanned PDFs aren't supported — use a text-layer PDF.",
            "errors": errors,
        })

    # 2. Load MOM regulations (cached, fast after first scrape).
    reg_data = get_regulations()
    regs = reg_data.get("regulations", [])

    # 3. LLM analysis. Timeouts surface as 504, never a frozen spinner (PM8).
    try:
        analysis = analyze_documents(documents, regs)
    except ValueError as e:
        raise HTTPException(502, detail=f"The analyser returned malformed output. {e}")
    except EnvironmentError as e:
        raise HTTPException(500, detail=str(e))
    except Exception as e:
        name = type(e).__name__.lower()
        if "timeout" in name:
            raise HTTPException(504, detail="Analysis timed out — please try again.")
        raise HTTPException(500, detail=f"Analysis error: {e}")

    # 4. Persist the session (parameterised — RT8).
    session_id = uuid.uuid4().hex[:8]
    conn = get_conn()
    try:
        conn.execute("""
            INSERT INTO sessions
                (id, created_at, filenames, doc_count, overall_severity, analysis, regulation_source)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            session_id,
            datetime.now().isoformat(),
            json.dumps([f.filename for f in files]),
            len(documents),
            analysis.get("overall_severity", "MODERATE"),
            json.dumps(analysis),
            reg_data.get("source"),
        ))
        conn.commit()
    finally:
        conn.close()

    return {
        "session_id": session_id,
        "docs_processed": len(documents),
        "docs_failed": len(errors),
        "extraction_errors": errors,
        "regulation_source": reg_data.get("source"),
        "analysis": analysis,
    }


# ── Sessions ─────────────────────────────────────────────────────────────────
@app.get("/api/sessions")
async def sessions():
    conn = get_conn()
    try:
        rows = conn.execute("""
            SELECT id, created_at, filenames, doc_count, overall_severity
            FROM sessions ORDER BY created_at DESC LIMIT 30
        """).fetchall()
    finally:
        conn.close()
    out = []
    for r in rows:
        d = dict(r)
        d["filenames"] = json.loads(d.get("filenames") or "[]")
        out.append(d)
    return out


@app.get("/api/session/{sid}")
async def session(sid: str):
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM sessions WHERE id = ?", (sid,)).fetchone()
    finally:
        conn.close()
    if not row:
        raise HTTPException(404, "Session not found.")
    d = dict(row)
    d["filenames"] = json.loads(d.get("filenames") or "[]")
    d["analysis"] = json.loads(d.get("analysis") or "{}")
    return d


# Mount static assets last so it never shadows the API routes.
if FRONTEND_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
