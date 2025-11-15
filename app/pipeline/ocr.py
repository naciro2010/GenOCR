"""Wrapper utilities around OCR execution with PaddleOCR and Tesseract fallback."""
from __future__ import annotations

import logging
import os
import shlex
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger("pdf2tables.pipeline")


def ocr_pdf(in_pdf: str, out_pdf: str, jobs: int) -> None:
    """Run OCRmyPDF to create a searchable PDF from a scanned PDF."""
    cmd = f"ocrmypdf --skip-text --rotate-pages --deskew --clean --optimize 1 --jobs {jobs} {shlex.quote(in_pdf)} {shlex.quote(out_pdf)}"
    subprocess.run(cmd, shell=True, check=True)


def ensure_ocr(in_pdf: Path, work_dir: Path) -> Path:
    """
    Run OCR using PaddleOCR (preferred) or Tesseract (fallback) and return the output path.

    The OCR engine can be controlled via environment variables:
    - USE_PADDLE_OCR=true/false (default: true)
    - PADDLE_OCR_LANG=fr/en/etc (default: fr)
    - PADDLE_OCR_GPU=true/false (default: false)
    """
    output_pdf = work_dir / f"{in_pdf.stem}-ocr.pdf"

    # Check if PaddleOCR should be used
    use_paddle = os.getenv("USE_PADDLE_OCR", "true").lower() == "true"

    if use_paddle:
        logger.info(
            "Attempting OCR with PaddleOCR",
            extra={"source": in_pdf.as_posix(), "engine": "PaddleOCR"}
        )

        # Try PaddleOCR first
        try:
            from .paddle_ocr import ocr_with_paddle

            lang = os.getenv("PADDLE_OCR_LANG", "fr")
            use_gpu = os.getenv("PADDLE_OCR_GPU", "false").lower() == "true"

            success = ocr_with_paddle(
                in_pdf=in_pdf,
                out_pdf=output_pdf,
                work_dir=work_dir,
                lang=lang,
                use_gpu=use_gpu
            )

            if success and output_pdf.exists():
                logger.info(
                    "OCR completed successfully with PaddleOCR",
                    extra={"output": output_pdf.as_posix()}
                )
                return output_pdf
            else:
                logger.warning(
                    "PaddleOCR processing did not produce output, falling back to Tesseract",
                    extra={"source": in_pdf.as_posix()}
                )

        except ImportError:
            logger.warning(
                "PaddleOCR not available, falling back to Tesseract",
                extra={"source": in_pdf.as_posix()}
            )
        except Exception as exc:
            logger.warning(
                "PaddleOCR failed, falling back to Tesseract",
                extra={"source": in_pdf.as_posix(), "error": str(exc)}
            )

    # Fallback to Tesseract/OCRmyPDF
    logger.info(
        "Running OCR with Tesseract/OCRmyPDF",
        extra={"source": in_pdf.as_posix(), "engine": "Tesseract"}
    )

    jobs = max(1, shutil.cpu_count() or 1)
    try:
        ocr_pdf(in_pdf.as_posix(), output_pdf.as_posix(), jobs)
        logger.info(
            "OCR completed successfully with Tesseract",
            extra={"output": output_pdf.as_posix()}
        )
        return output_pdf
    except Exception as exc:  # pragma: no cover - depends on OCR install
        logger.exception("OCRmyPDF failed", extra={"source": in_pdf.as_posix()})
        raise RuntimeError("OCR pipeline failed") from exc

