"""API endpoints powering the pdf2tables-saas frontend."""
from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from .limits import limiter
from .pipeline import render as render_utils
from .pipeline import run_pipeline

router = APIRouter()


def get_registry(request: Request):
    return request.app.state.registry



class ExtractPayload(BaseModel):
    request_id: str
    file_name: str


@router.post("/extract")
@limiter.limit("15/minute")
async def extract(
    payload: ExtractPayload,
    registry=Depends(get_registry),
):
    record = registry.get(payload.request_id)
    if not record:
        raise HTTPException(status_code=404, detail="Request not found")

    file_status = record.files.get(payload.file_name)
    if not file_status:
        raise HTTPException(status_code=404, detail="File not found")

    source_path = record.directory / payload.file_name
    if not source_path.exists():
        raise HTTPException(status_code=404, detail="Source file missing")

    result = await asyncio.to_thread(run_pipeline, source_path, record.directory)
    output_dir = record.directory / payload.file_name
    output_dir.mkdir(parents=True, exist_ok=True)
    html_path = output_dir / "tables.html"
    json_path = output_dir / "tables.json"
    html_path.write_text(result.html, encoding="utf-8")
    json_path.write_text(
        render_utils.serialize_metadata(result.metadata),
        encoding="utf-8",
    )
    registry.update(
        payload.request_id,
        payload.file_name,
        status="finished",
        progress=100,
        html_path=html_path,
        json_path=json_path,
    )
    return {"status": "ok", "tables": result.tables_found}


@router.get("/status/{request_id}")
@limiter.limit("60/minute")
async def status_endpoint(request_id: str, registry=Depends(get_registry)):
    files = registry.list_files(request_id)
    if not files:
        raise HTTPException(status_code=404, detail="Request not found")
    payload = []
    done = True
    for file_status in files:
        payload.append(
            {
                "name": file_status.display_name,
                "slug": file_status.name,
                "status": file_status.status,
                "progress": file_status.progress,
                "error": file_status.error,
            }
        )
        if file_status.status not in {"finished", "error"}:
            done = False
    return {"files": payload, "done": done}



@router.post("/cancel/{request_id}/{file_slug}")
@limiter.limit("60/minute")
async def cancel(request_id: str, file_slug: str, registry=Depends(get_registry)):
    record = registry.get(request_id)
    if not record:
        raise HTTPException(status_code=404, detail="Request not found")
    if file_slug not in record.files:
        raise HTTPException(status_code=404, detail="File not found")
    registry.cancel(request_id, file_slug)
    return {"status": "cancelled"}

@router.get("/download/{request_id}/{file_slug}")
@limiter.limit("60/minute")
async def download(request_id: str, file_slug: str, registry=Depends(get_registry)):
    record = registry.get(request_id)
    if not record:
        raise HTTPException(status_code=404, detail="Request not found")

    allowed_extensions = {"html": "tables.html", "json": "tables.json"}
    try:
        slug, ext = file_slug.rsplit(".", 1)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid download path") from None

    if ext not in allowed_extensions:
        raise HTTPException(status_code=415, detail="Unsupported download format")

    status = record.files.get(slug)
    if not status:
        raise HTTPException(status_code=404, detail="File not found")

    target_attr = "html_path" if ext == "html" else "json_path"
    target_path = getattr(status, target_attr)
    if not target_path or not Path(target_path).exists():
        raise HTTPException(status_code=404, detail="Requested output missing")

    filename = f"{Path(status.display_name).stem}.{ext}"
    media_type = "text/html" if ext == "html" else "application/json"
    return FileResponse(target_path, filename=filename, media_type=media_type)

