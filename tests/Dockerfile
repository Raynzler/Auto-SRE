# Runs the full reliability test suite in a container.
# Build context is the repo root (see docker-compose.test.yml).
FROM python:3.12-slim

WORKDIR /app
COPY . /app

RUN pip install --no-cache-dir -r requirements-dev.txt

# Reports are written to /app (coverage.xml, htmlcov/) — mount /app to keep them.
CMD ["pytest"]
