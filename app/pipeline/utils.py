"""Utility helpers for file management and validation."""
from __future__ import annotations

import hashlib
import mimetypes
import os
import shutil
import tempfile
from pathlib import Path
from typing import Iterable

from fastapi import HTTPException, UploadFile

ALLOWED_MIME_TYPES = {"application/pdf", "image/png", "image/jpeg"}
DEFAULT_MAX_CONTENT_LENGTH = 25 * 1024 * 1024  # 25 MB


def max_upload_bytes() -> int:
    try:
        value = int(os.getenv("MAX_CONTENT_LENGTH", str(DEFAULT_MAX_CONTENT_LENGTH)))
    except ValueError:
        value = DEFAULT_MAX_CONTENT_LENGTH
    return value


def hashed_filename(filename: str) -> str:
    digest = hashlib.sha256(filename.encode("utf-8", errors="ignore")).hexdigest()
    suffix = Path(filename).suffix.lower()
    return f"{digest}{suffix}"


def ensure_allowed_mime(upload: UploadFile) -> None:
    content_type = upload.content_type or "application/octet-stream"
    if content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=415, detail="Unsupported media type")


def safe_save_upload(upload: UploadFile, destination: Path) -> int:
    """Stream upload to disk enforcing size limits."""
    ensure_allowed_mime(upload)
    limit = max_upload_bytes()
    size = 0
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as f:
        while True:
            chunk = upload.file.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > limit:
                upload.file.close()
                f.close()
                destination.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail="File too large")
            f.write(chunk)
    upload.file.close()
    return size


def guess_mimetype(path: Path) -> str:
    mime, _ = mimetypes.guess_type(path.name)
    if mime:
        return mime
    if path.suffix.lower() == ".pdf":
        return "application/pdf"
    if path.suffix.lower() in {".png", ".jpg", ".jpeg"}:
        return "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    return "application/octet-stream"


def ensure_pdf(path: Path) -> Path:
    """If the given path is an image, convert it to a temporary PDF."""
    if path.suffix.lower() == ".pdf":
        return path

    import fitz

    pdf_path = path.with_suffix(".pdf")
    doc = fitz.open()
    image = fitz.open(path.as_posix())
    try:
        rect = image[0].rect
        pdf_bytes = image.convert_to_pdf()
        pdf_doc = fitz.open("pdf", pdf_bytes)
        page = doc.new_page(width=rect.width, height=rect.height)
        page.show_pdf_page(rect, pdf_doc, 0)
        doc.save(pdf_path.as_posix())
    finally:
        image.close()
        doc.close()
    return pdf_path


def temp_request_dir(request_id: str) -> Path:
    base = Path(tempfile.gettempdir()) / f"pdf2tables-{request_id}"
    base.mkdir(parents=True, exist_ok=True)
    return base


def cleanup_directory(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path, ignore_errors=True)


def cleanup_later(path: Path, delay_seconds: int = 3600) -> None:
    import threading

    def _cleanup() -> None:
        try:
            threading.Event().wait(delay_seconds)
            cleanup_directory(path)
        except Exception:
            pass

    threading.Thread(target=_cleanup, daemon=True).start()


def stage_progress(stage: str) -> int:
    stages: Iterable[str] = ["received", "decide", "ocr", "extract", "render"]
    mapping = {name: int(index * (100 / (len(stages) - 1))) for index, name in enumerate(stages)}
    return mapping.get(stage, 0)

