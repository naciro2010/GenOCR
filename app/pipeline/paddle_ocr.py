"""PaddleOCR-based OCR extraction with image preprocessing."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF
from PIL import Image

logger = logging.getLogger("pdf2tables.pipeline")


def pdf_to_images(pdf_path: Path, output_dir: Path, dpi: int = 300) -> list[Path]:
    """Convert PDF pages to images for PaddleOCR processing."""
    doc = fitz.open(pdf_path.as_posix())
    image_paths = []

    try:
        for page_num, page in enumerate(doc):
            # Render page to pixmap
            mat = fitz.Matrix(dpi / 72, dpi / 72)
            pix = page.get_pixmap(matrix=mat)

            # Save as PNG
            img_path = output_dir / f"page_{page_num + 1}.png"
            pix.save(img_path.as_posix())
            image_paths.append(img_path)

            logger.debug(
                f"Converted page {page_num + 1} to image",
                extra={"page": page_num + 1, "output": img_path.as_posix()}
            )
    finally:
        doc.close()

    return image_paths


def ocr_with_paddle(
    in_pdf: Path,
    out_pdf: Path,
    work_dir: Path,
    lang: str = "fr",
    use_gpu: bool = False
) -> bool:
    """
    OCR a PDF using PaddleOCR and create a searchable PDF.

    Args:
        in_pdf: Input PDF path
        out_pdf: Output PDF path
        work_dir: Working directory for temporary files
        lang: Language code (fr, en, etc.)
        use_gpu: Whether to use GPU acceleration

    Returns:
        True if successful, False otherwise
    """
    try:
        from paddleocr import PaddleOCR
        import cv2
        import numpy as np
    except ImportError as e:
        logger.warning(
            "PaddleOCR not available, falling back to Tesseract",
            extra={"error": str(e)}
        )
        return False

    try:
        # Initialize PaddleOCR
        ocr = PaddleOCR(
            use_angle_cls=True,  # Enable angle classification
            lang=lang,
            use_gpu=use_gpu,
            show_log=False
        )

        # Create temp directory for images
        img_dir = work_dir / "paddle_images"
        img_dir.mkdir(exist_ok=True)

        # Convert PDF to images
        logger.info(
            "Converting PDF to images for PaddleOCR",
            extra={"pdf": in_pdf.as_posix()}
        )
        image_paths = pdf_to_images(in_pdf, img_dir)

        # Process each image with PaddleOCR
        all_results = []
        for idx, img_path in enumerate(image_paths):
            logger.info(
                f"Processing page {idx + 1}/{len(image_paths)} with PaddleOCR",
                extra={"page": idx + 1, "image": img_path.as_posix()}
            )

            result = ocr.ocr(img_path.as_posix(), cls=True)
            all_results.append(result)

        # Create searchable PDF using PyMuPDF
        logger.info("Creating searchable PDF", extra={"output": out_pdf.as_posix()})
        create_searchable_pdf(in_pdf, out_pdf, all_results, image_paths)

        logger.info(
            "PaddleOCR processing completed successfully",
            extra={"pages": len(image_paths), "output": out_pdf.as_posix()}
        )
        return True

    except Exception as exc:
        logger.exception(
            "PaddleOCR processing failed",
            extra={"source": in_pdf.as_posix(), "error": str(exc)}
        )
        return False


def create_searchable_pdf(
    original_pdf: Path,
    output_pdf: Path,
    ocr_results: list,
    image_paths: list[Path]
) -> None:
    """Create a searchable PDF by adding OCR text layer to original PDF."""
    doc = fitz.open(original_pdf.as_posix())

    try:
        for page_num, (page, result) in enumerate(zip(doc, ocr_results)):
            if result is None or len(result) == 0:
                continue

            # PaddleOCR returns: [[[bbox], (text, confidence)], ...]
            for line in result[0] if result[0] else []:
                if len(line) < 2:
                    continue

                bbox, (text, confidence) = line

                # Skip low confidence results
                if confidence < 0.5:
                    continue

                # Extract bounding box coordinates
                # bbox format: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                x_coords = [point[0] for point in bbox]
                y_coords = [point[1] for point in bbox]
                x0, y0 = min(x_coords), min(y_coords)
                x1, y1 = max(x_coords), max(y_coords)

                # Get page dimensions from image
                img = Image.open(image_paths[page_num])
                img_width, img_height = img.size

                # Convert image coordinates to PDF coordinates
                page_rect = page.rect
                scale_x = page_rect.width / img_width
                scale_y = page_rect.height / img_height

                pdf_x0 = x0 * scale_x
                pdf_y0 = y0 * scale_y
                pdf_x1 = x1 * scale_x
                pdf_y1 = y1 * scale_y

                # Add invisible text annotation
                rect = fitz.Rect(pdf_x0, pdf_y0, pdf_x1, pdf_y1)

                # Insert text as invisible layer (render_mode=3 means invisible)
                page.insert_textbox(
                    rect,
                    text,
                    fontsize=12,
                    render_mode=3,  # Invisible text
                    color=(0, 0, 0)
                )

        # Save the searchable PDF
        doc.save(output_pdf.as_posix())
        logger.info(
            "Searchable PDF created",
            extra={"output": output_pdf.as_posix(), "pages": len(doc)}
        )

    finally:
        doc.close()
