# pdf2tables-saas

[![CI](https://github.com/your-org/pdf2tables-saas/actions/workflows/deploy.yml/badge.svg)](https://github.com/your-org/pdf2tables-saas/actions/workflows/deploy.yml)
[![Hugging Face Space](https://img.shields.io/badge/Spaces-pdf2tables--saas-blue?logo=huggingface)](https://huggingface.co/spaces/your-username/pdf2tables-saas)

Production-ready SaaS starter for extracting tables from PDFs or images with a privacy-aware FastAPI backend, HTMX-powered UI, and a Docker deployment on Hugging Face Spaces.

> Demo animation placeholder — add your own GIF at `docs/demo.gif` if desired.

## Architecture

```
┌────────────────────────────────────────────────────────────┐
│                        FastAPI app                         │
│                                                            │
│  Views (Jinja2) ──► Upload queue ──► Registry ──► Pipeline │
│      ▲                    │              │             │   │
│      │                    │              │             ▼   │
│   HTMX polling ◄──────────┴── Status JSON │    Render HTML │
│                             │             │    + metadata │
│                             │             ▼                │
│                         SlowAPI limiter + logging          │
└────────────────────────────────────────────────────────────┘
            │                                │
            ▼                                ▼
   OCRmyPDF + Camelot                 Temp storage cleanup
```

### Extraction pipeline

1. **Heuristic** — PyMuPDF estimates whether the PDF is born-digital or scanned.
2. **OCR pass** — When needed, OCRmyPDF runs rotate/deskew/clean to rebuild searchable PDF.
3. **Table parsing** — Camelot attempts `lattice` first, falls back to `stream` if no tables.
4. **Rendering** — Tables are rendered as responsive HTML with optional JSON download.
5. **Observability** — Structured JSON logs capture request IDs, timings, and stage outcomes.

A `USE_DEEP_TABLES=true` environment flag exposes a hook for plugging in neural table models later without forcing heavy dependencies today.

## Features

- Multi-file upload with progress, cancellation, and accessible status cards.
- Automatic OCR with Tesseract/Ghostscript for scanned documents.
- Born-digital PDF table extraction via Camelot lattice/stream.
- HTML preview plus downloadable HTML and JSON metadata per file.
- Security controls: file-type enforcement, 25 MB limit (tunable), SlowAPI rate limiting, strict security headers.
- Observability via structured logs and request IDs; `/healthz` endpoint for probes.
- Fully containerized for Hugging Face Docker Spaces with CI-driven deploys.

## Getting started

### Prerequisites (Ubuntu/Debian)

```bash
sudo apt-get update && sudo apt-get install -y python3.11 python3.11-venv \
  tesseract-ocr ghostscript poppler-utils
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Local development

```bash
export MAX_CONTENT_LENGTH=$((25 * 1024 * 1024))
export APP_ORIGIN="http://127.0.0.1:8000"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open <http://127.0.0.1:8000> to upload PDFs or images. Processing happens synchronously in development; uploads are removed after 60 minutes.

### Running tests

```bash
pytest -q
```

Set `SYNC_PIPELINE=true` during tests to force inline processing; the test suite handles this automatically.

## Deployment

### Docker build

```bash
docker build -t pdf2tables-saas .
docker run --rm -e PORT=7860 -p 7860:7860 pdf2tables-saas
```

The container listens on `$PORT` (default 7860) and exposes `/healthz` for health checks.

### Hugging Face Space

1. Create a **Docker Space** at <https://huggingface.co/spaces>.
2. Add a `HF_TOKEN` secret to the GitHub repository.
3. Update `.github/workflows/deploy.yml` with your `<YOUR_HF_USERNAME>/<YOUR_SPACE_NAME>`.
4. Push to `main` — CI runs tests and mirrors the repo to the Space via `huggingface-cli upload`.

## Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `MAX_CONTENT_LENGTH` | `26214400` | Max upload size in bytes (per file). |
| `APP_ORIGIN` | unset | Optional explicit CORS origin. |
| `USE_DEEP_TABLES` | `false` | Enable placeholder hook for deep table extraction. |
| `SYNC_PIPELINE` | `false` | Run pipeline inline (useful for tests). |
| `PORT` | `7860` | HTTP port inside the container. |

## Usage & privacy

- Uploads are stored in `/tmp/pdf2tables-<request-id>` directories.
- Temporary directories are scheduled for cleanup after 60 minutes.
- No data is persisted beyond the processing window; do not upload sensitive information.
- Rate limits (30 requests/min/IP) protect against abuse.

## Known limitations

- Borderless tables or complex multi-line cells may require deep models (hook provided).
- Encrypted or password-protected PDFs are rejected by upstream libraries.
- Camelot requires Ghostscript/Poppler; install per Dockerfile if running elsewhere.

## Extending

- Fork the repo and update `make_pr` secrets for custom deployments.
- Enable deep-learning extractors by overriding the placeholder in `app/pipeline/__init__.py`.
- Add persistent storage or background workers by swapping the in-memory registry for Redis.

## Troubleshooting

| Issue | Fix |
| --- | --- |
| `415 Unsupported Media Type` | Ensure files are PDF/PNG/JPG with proper mimetype. |
| `413 Payload Too Large` | Lower file size or raise `MAX_CONTENT_LENGTH`. |
| OCR errors | Confirm `ocrmypdf`, Tesseract, and Ghostscript are installed (see Dockerfile). |
| Camelot finds 0 tables | Try adjusting `USE_DEEP_TABLES` or supply higher-quality scans. |

## License

[MIT](LICENSE)
