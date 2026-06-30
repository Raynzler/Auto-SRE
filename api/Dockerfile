# Build context is the repo root (see docker-compose) so the shared package is
# available. Each service image installs autosre-shared, then its own code.
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY shared /tmp/shared
RUN pip install --no-cache-dir /tmp/shared && rm -rf /tmp/shared

COPY api/main.py /app/main.py

# Run as a non-root user; pre-create the (named-volume) data dir it owns.
RUN useradd -r -u 10001 appuser \
    && mkdir -p /app/data \
    && chown -R appuser /app
USER 10001

EXPOSE 8000

# Liveness probe (reads PORT at runtime; distroless-free Python image has urllib).
HEALTHCHECK --interval=15s --timeout=3s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import os,urllib.request,sys; p=os.environ.get('PORT','8000'); sys.exit(0 if urllib.request.urlopen(f'http://127.0.0.1:{p}/health',timeout=2).status==200 else 1)"]

CMD ["python", "main.py"]
