# Dockerfile (multi-stage simplified)
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr ghostscript poppler-utils curl fonts-dejavu \
    libgomp1 libglib2.0-0 libsm6 libxext6 libxrender-dev libgl1-mesa-glx && \
    rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY pyproject.toml requirements.txt* /app/
RUN pip install --upgrade pip && \
    pip install fastapi uvicorn[standard] jinja2 pymupdf camelot-py[cv] ocrmypdf \
    paddleocr paddlepaddle pandas slowapi python-multipart
COPY app /app/app
COPY templates /app/app/templates
COPY static /app/app/static
ENV PORT=7860
EXPOSE 7860
HEALTHCHECK CMD curl -fsS http://127.0.0.1:${PORT}/healthz || exit 1
USER 65532
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
