"""
app.py
ClauseGuard -- upload a contract PDF, get plain-English summary + red flags,
validated/hashed in a Daytona sandbox, signed via Terminal 3.

Run: streamlit run app.py

Required env vars: TOKENROUTER_API_KEY, DAYTONA_API_KEY,
                    TERMINAL3_API_KEY, TERMINAL3_DID
"""

import streamlit as st
import pdfplumber

from src.analyzer import analyze
from src.sandbox_validate import validate_and_hash
from src.terminal3_signer import sign_report_hash

st.set_page_config(page_title="ClauseGuard", page_icon="\U0001f4dc")

st.title("ClauseGuard")
st.caption("Upload an employment contract -- get a plain-English summary and red flags.")

st.warning(
    "Not legal advice and not exhaustive. Highlights clauses worth discussing "
    "with HR or a free legal advisor (e.g. probono.sg). 'No red flags found' "
    "does not guarantee a contract is fair. Singapore employment contracts "
    "(MVP scope)."
)

uploaded = st.file_uploader("Upload contract PDF", type=["pdf"])

if uploaded and st.button("Analyze"):
    try:
        with st.status("Running ClauseGuard...", expanded=True) as status:
            st.write("1/3 Extracting text from PDF...")
            with pdfplumber.open(uploaded) as pdf:
                text = "\n".join(page.extract_text() or "" for page in pdf.pages)
            st.success(f"Extracted {len(text)} characters.")

            st.write("2/3 Analyzing against red-flag checklist...")
            report = analyze(text)
            st.success(f"Found {len(report.get('red_flags', []))} flags.")

            st.write("3/3 Validating + signing report (Daytona + Terminal 3)...")
            validation = validate_and_hash(report)
            receipt = sign_report_hash(validation["report_hash"])
            status.update(label="Done", state="complete")

        st.subheader("Plain-English Summary")
        st.write(report["plain_english_summary"])

        st.subheader("Red Flags")
        severity_color = {"serious": "\U0001f534", "moderate": "\U0001f7e1", "info": "\U0001f535"}
        for flag in report.get("red_flags", []):
            icon = severity_color.get(flag.get("severity"), "\u26aa")
            with st.expander(f"{icon} {flag['issue'][:80]}..."):
                st.write(f"**Clause:** {flag['clause']}")
                st.write(f"**Issue:** {flag['issue']}")
                st.write(f"**Severity:** {flag['severity']}")
                if flag.get("regulation_lookup"):
                    st.caption("Flagged for live regulation lookup (not yet wired in this build)")

        st.subheader("Attestation Receipt")
        st.json({"validation": validation, "terminal3": receipt})

    except Exception as e:
        st.error(f"Pipeline failed: {e}")