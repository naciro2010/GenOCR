"""Determine whether a PDF likely requires OCR."""
from __future__ import annotations

from pathlib import Path

import fitz


def is_scanned_pdf(path: Path, text_ratio_threshold: float = 0.1) -> bool:
    """Return True if the document appears to be image-based only."""
    doc = fitz.open(path.as_posix())
    try:
        total_text = 0
        total_pages = doc.page_count or 1
        for page in doc:
            text = page.get_text("text", sort=True)
            total_text += len(text.strip())
        ratio = total_text / (total_pages * 1000)
        return ratio < text_ratio_threshold
    finally:
        doc.close()

