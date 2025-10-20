from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import app

SAMPLE_PDF_BYTES = b"%PDF-1.4\n%pdf2tables test fixture\n1 0 obj<< /Type /Catalog >>endobj\nxref\n0 1\n0000000000 65535 f \ntrailer\n<< /Root 1 0 R /Size 1 >>\nstartxref\n0\n%%EOF"


def test_upload_flow(monkeypatch):
    client = TestClient(app)

    async def fake_to_thread(func, *args, **kwargs):
        return func(*args, **kwargs)

    monkeypatch.setenv("SYNC_PIPELINE", "true")
    monkeypatch.setattr("app.views.asyncio.to_thread", fake_to_thread)

    def fake_pipeline(path, work_dir):
        return SimpleNamespace(
            html="<table><tr><td>42</td></tr></table>",
            metadata={"tables": [{"page": 1, "order": 1, "flavor": "lattice", "data": [["42"]]}]},
            tables_found=1,
            scanned=False,
            source_pdf=path,
        )

    monkeypatch.setattr("app.views.run_pipeline", fake_pipeline)

    resp_index = client.get("/")
    assert resp_index.status_code == 200

    response = client.post(
        "/upload",
        files=[("files", ("sample.pdf", SAMPLE_PDF_BYTES, "application/pdf"))],
    )
    assert response.status_code == 303
    result_location = response.headers["location"]
    assert result_location.startswith("/result/")

    result_page = client.get(result_location)
    assert result_page.status_code == 200
    assert "Extraction queue" in result_page.text

    request_id = result_location.rsplit("/", 1)[-1]
    partial = client.get(f"/partials/status/{request_id}")
    assert partial.status_code == 200
    assert "Download HTML" in partial.text

    status_json = client.get(f"/api/status/{request_id}")
    assert status_json.status_code == 200
    payload = status_json.json()
    assert payload["files"][0]["status"] in {"finished", "error", "cancelled"}

