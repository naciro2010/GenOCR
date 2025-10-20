"""Pipeline orchestration for pdf2tables-saas."""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path

from . import decide, native, render, utils
from .ocr import ensure_ocr

logger = logging.getLogger("pdf2tables.pipeline")


@dataclass
class PipelineResult:
    html: str
    metadata: dict
    tables_found: int
    scanned: bool
    source_pdf: Path


def run_pipeline(source: Path, work_dir: Path) -> PipelineResult:
    work_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = utils.ensure_pdf(source)
    logger.info("Deciding pipeline", extra={"file": pdf_path.as_posix()})
    scanned = decide.is_scanned_pdf(pdf_path)

    processed_pdf = pdf_path
    if scanned:
        logger.info("Running OCR", extra={"file": pdf_path.as_posix()})
        processed_pdf = ensure_ocr(pdf_path, work_dir)

    tables = native.extract_tables(processed_pdf)
    if not tables and os.getenv("USE_DEEP_TABLES", "false").lower() == "true":
        logger.info("Deep table hook placeholder", extra={"file": processed_pdf.as_posix()})
        # Placeholder for deep learning based extraction; to be implemented later.

    html, metadata = render.render_tables(tables)
    metadata.update(
        {
            "scanned": scanned,
            "tables_found": len(metadata.get("tables", [])),
            "source": processed_pdf.name,
        }
    )
    return PipelineResult(
        html=html,
        metadata=metadata,
        tables_found=len(tables),
        scanned=scanned,
        source_pdf=processed_pdf,
    )

