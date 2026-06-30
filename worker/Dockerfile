# Build context is the repo root so the shared package is available.
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY shared /tmp/shared
RUN pip install --no-cache-dir /tmp/shared && rm -rf /tmp/shared

COPY worker/main.py /app/main.py

RUN useradd -r -u 10001 appuser \
    && mkdir -p /app/data \
    && chown -R appuser /app
USER 10001

EXPOSE 8002

HEALTHCHECK --interval=15s --timeout=3s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import os,urllib.request,sys; p=os.environ.get('PORT','8002'); sys.exit(0 if urllib.request.urlopen(f'http://127.0.0.1:{p}/health',timeout=2).status==200 else 1)"]

CMD ["python", "main.py"]
