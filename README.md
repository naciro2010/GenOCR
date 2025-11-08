# GenOCR - PDF to Tables Extractor

[![CI](https://github.com/naciro2010/GenOCR/actions/workflows/deploy.yml/badge.svg)](https://github.com/naciro2010/GenOCR/actions/workflows/deploy.yml)

**GenOCR** est une application SaaS production-ready pour extraire des tableaux depuis des PDFs ou images, avec un backend FastAPI sécurisé, une interface HTMX moderne, et un déploiement Docker sur Hugging Face Spaces.

🚀 **Fonctionnalités principales:**
- Extraction intelligente de tableaux depuis PDFs (natifs ou scannés)
- OCR automatique avec Tesseract pour documents scannés
- Interface web moderne avec upload multi-fichiers
- Export HTML et JSON des tableaux extraits
- Sécurité renforcée et rate limiting
- Déploiement facile sur Hugging Face Spaces

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

### Déploiement sur Hugging Face Space

GenOCR peut être déployé gratuitement sur Hugging Face Spaces:

1. Créez un **Docker Space** sur <https://huggingface.co/spaces>
2. Nommez votre Space (ex: `votre-username/genocr`)
3. Ajoutez un secret `HF_TOKEN` dans les settings GitHub du repo
4. Mettez à jour `.github/workflows/deploy.yml` avec votre username/space-name
5. Pushez sur `main` — le CI déploiera automatiquement

**Alternative: Déploiement manuel**
```bash
# Installez le CLI Hugging Face
pip install huggingface-hub

# Login
huggingface-cli login

# Upload vers votre Space
huggingface-cli upload votre-username/genocr . --repo-type=space
```

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

## Déploiements gratuits recommandés

GenOCR peut être déployé gratuitement sur plusieurs plateformes:

1. **Hugging Face Spaces** (Recommandé) - 16GB RAM, GPU optionnel
2. **Render.com** - Free tier avec 512MB RAM
3. **Railway.app** - $5 de crédit gratuit/mois
4. **Fly.io** - Free tier généreux

## Extension et personnalisation

- Forkez le repo pour des déploiements personnalisés
- Activez l'extraction deep-learning en modifiant `app/pipeline/__init__.py`
- Ajoutez du stockage persistant avec Redis ou PostgreSQL
- Intégrez d'autres modèles OCR (EasyOCR, PaddleOCR, etc.)

## Dépannage

| Issue | Fix |
| --- | --- |
| `415 Unsupported Media Type` | Ensure files are PDF/PNG/JPG with proper mimetype. |
| `413 Payload Too Large` | Lower file size or raise `MAX_CONTENT_LENGTH`. |
| OCR errors | Confirm `ocrmypdf`, Tesseract, and Ghostscript are installed (see Dockerfile). |
| Camelot finds 0 tables | Try adjusting `USE_DEEP_TABLES` or supply higher-quality scans. |

## License

[MIT](LICENSE)
