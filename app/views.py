"""HTTP views for the pdf2tables-saas application."""
from __future__ import annotations

import asyncio
import os
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from .pipeline import run_pipeline
from .pipeline import render as render_utils
from .pipeline import utils as pipeline_utils
from .state import FileStatus

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


def get_registry(request: Request):
    return request.app.state.registry


@router.get("/")
async def index(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request},
    )


@router.post("/upload")
async def upload(
    request: Request,
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    registry=Depends(get_registry),
):
    if not files:
        raise HTTPException(status_code=422, detail="No files uploaded")

    request_id = uuid.uuid4().hex
    work_dir = pipeline_utils.temp_request_dir(request_id)
    registry.create_request(request_id, work_dir)

    saved_files: list[tuple[str, Path]] = []

    for upload_file in files:
        original_name = upload_file.filename or "uploaded"
        hashed = pipeline_utils.hashed_filename(original_name)
        dest = work_dir / hashed
        await asyncio.to_thread(pipeline_utils.safe_save_upload, upload_file, dest)
        status = FileStatus(name=hashed, display_name=original_name)
        registry.add_file(request_id, status)
        registry.update(request_id, hashed, status="queued", progress=pipeline_utils.stage_progress("received"))
        saved_files.append((hashed, dest))

    async def process_queue() -> None:
        for hashed, path in saved_files:
            try:
                record = registry.get(request_id)
                entry = record.files.get(hashed) if record else None
                if entry and entry.status == "cancelled":
                    continue
                registry.update(request_id, hashed, status="processing", progress=pipeline_utils.stage_progress("decide"))
                result = await asyncio.to_thread(run_pipeline, path, work_dir)
                registry.update(request_id, hashed, progress=pipeline_utils.stage_progress("extract"))
                output_dir = work_dir / hashed
                output_dir.mkdir(parents=True, exist_ok=True)
                html_path = output_dir / "tables.html"
                json_path = output_dir / "tables.json"
                html_path.write_text(result.html, encoding="utf-8")
                registry.update(request_id, hashed, progress=pipeline_utils.stage_progress("render"))
                json_path.write_text(
                    render_utils.serialize_metadata(result.metadata),
                    encoding="utf-8",
                )
                registry.update(
                    request_id,
                    hashed,
                    status="finished",
                    progress=100,
                    html_path=html_path,
                    json_path=json_path,
                )
            except HTTPException as exc:
                registry.mark_error(request_id, hashed, str(exc.detail))
            except Exception as exc:  # pragma: no cover - defensive branch
                registry.mark_error(request_id, hashed, str(exc))

        pipeline_utils.cleanup_later(work_dir)

    if os.getenv("SYNC_PIPELINE", "false").lower() == "true":
        await process_queue()
    else:
        asyncio.create_task(process_queue())

    background_tasks.add_task(lambda: None)  # ensure background tasks used for cleanup compatibility

    return RedirectResponse(url=f"/result/{request_id}", status_code=303)


@router.get("/result/{request_id}")
async def result(request: Request, request_id: str, registry=Depends(get_registry)):
    record = registry.get(request_id)
    if not record:
        raise HTTPException(status_code=404, detail="Request not found")
    return templates.TemplateResponse(
        "result.html",
        {
            "request": request,
            "request_id": request_id,
            "files": registry.list_files(request_id),
        },
    )


@router.get("/partials/status/{request_id}")
async def status_partial(request: Request, request_id: str, registry=Depends(get_registry)):
    record = registry.get(request_id)
    if not record:
        raise HTTPException(status_code=404, detail="Request not found")
    return templates.TemplateResponse(
        "status_partial.html",
        {
            "request": request,
            "request_id": request_id,
            "files": registry.list_files(request_id),
        },
    )


@router.get("/error")
async def error_page(request: Request):
    return templates.TemplateResponse("error.html", {"request": request})

