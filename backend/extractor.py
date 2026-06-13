"""
Multi-PDF text extractor using pdfplumber.
Returns structured text per document for downstream analysis.
"""
import io
import pdfplumber


def extract_text(file_bytes: bytes, filename: str) -> dict:
    """
    Extract text from a PDF's bytes.
    Returns: {filename, success, text, pages, chars, error?}
    """
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            page_texts = []
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                if text.strip():
                    page_texts.append(f"[Page {i+1}]\n{text.strip()}")

            full_text = "\n\n".join(page_texts)

            if not full_text.strip():
                return {
                    "filename": filename,
                    "success": False,
                    "error": "No extractable text — likely a scanned or image-only PDF.",
                    "text": "",
                    "pages": len(pdf.pages),
                    "chars": 0,
                }

            return {
                "filename": filename,
                "success": True,
                "text": full_text,
                "pages": len(pdf.pages),
                "chars": len(full_text),
            }
    except Exception as e:
        return {
            "filename": filename,
            "success": False,
            "error": str(e),
            "text": "",
            "pages": 0,
            "chars": 0,
        }