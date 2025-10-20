"""State management for extraction requests."""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class FileStatus:
    name: str
    display_name: str
    status: str = "pending"
    progress: int = 0
    error: Optional[str] = None
    html_path: Optional[Path] = None
    json_path: Optional[Path] = None
    started_at: float = field(default_factory=time.time)
    finished_at: Optional[float] = None


@dataclass
class RequestRecord:
    request_id: str
    directory: Path
    created_at: float = field(default_factory=time.time)
    files: Dict[str, FileStatus] = field(default_factory=dict)


class RequestRegistry:
    """Thread-safe in-memory registry for tracking work."""

    def __init__(self) -> None:
        self._records: Dict[str, RequestRecord] = {}
        self._lock = threading.RLock()

    def create_request(self, request_id: str, directory: Path) -> RequestRecord:
        with self._lock:
            record = RequestRecord(request_id=request_id, directory=directory)
            self._records[request_id] = record
            return record

    def get(self, request_id: str) -> Optional[RequestRecord]:
        with self._lock:
            return self._records.get(request_id)

    def add_file(self, request_id: str, status: FileStatus) -> None:
        with self._lock:
            record = self._records[request_id]
            record.files[status.name] = status

    def list_files(self, request_id: str) -> List[FileStatus]:
        with self._lock:
            record = self._records.get(request_id)
            if not record:
                return []
            return list(record.files.values())

    def update(
        self,
        request_id: str,
        file_name: str,
        *,
        status: Optional[str] = None,
        progress: Optional[int] = None,
        error: Optional[str] = None,
        html_path: Optional[Path] = None,
        json_path: Optional[Path] = None,
    ) -> None:
        with self._lock:
            record = self._records[request_id]
            entry = record.files[file_name]
            if status is not None:
                entry.status = status
            if progress is not None:
                entry.progress = progress
            if error is not None:
                entry.error = error
            if html_path is not None:
                entry.html_path = html_path
            if json_path is not None:
                entry.json_path = json_path
            if status in {"finished", "error"}:
                entry.finished_at = time.time()

    def mark_error(self, request_id: str, file_name: str, message: str) -> None:
        self.update(
            request_id,
            file_name,
            status="error",
            progress=100,
            error=message,
        )

    def cancel(self, request_id: str, file_name: str) -> None:
        with self._lock:
            record = self._records.get(request_id)
            if not record or file_name not in record.files:
                return
            entry = record.files[file_name]
            entry.status = "cancelled"
            entry.progress = 100
            entry.finished_at = time.time()

    def cleanup(self, request_id: str) -> None:
        with self._lock:
            self._records.pop(request_id, None)

