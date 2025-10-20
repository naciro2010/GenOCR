# app/pipeline/ocr.py (skeleton)
def ocr_pdf(in_pdf: str, out_pdf: str, jobs: int) -> None:
    import subprocess, shlex
    cmd = f"ocrmypdf --skip-text --rotate-pages --deskew --clean --optimize 1 --jobs {jobs} {shlex.quote(in_pdf)} {shlex.quote(out_pdf)}"
    subprocess.run(cmd, shell=True, check=True)

"""Wrapper utilities around OCRmyPDF execution."""
from __future__ import annotations

import logging
import shutil
from pathlib import Path

logger = logging.getLogger("pdf2tables.pipeline")


def ensure_ocr(in_pdf: Path, work_dir: Path) -> Path:
    """Run OCR if available and return the output path."""
    jobs = max(1, shutil.cpu_count() or 1)
    output_pdf = work_dir / f"{in_pdf.stem}-ocr.pdf"
    try:
        ocr_pdf(in_pdf.as_posix(), output_pdf.as_posix(), jobs)
        return output_pdf
    except Exception as exc:  # pragma: no cover - depends on OCR install
        logger.exception("OCRmyPDF failed", extra={"source": in_pdf.as_posix()})
        raise RuntimeError("OCR pipeline failed") from exc

