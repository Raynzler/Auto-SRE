# Runs the full reliability test suite in a container.
# Build context is the repo root (see docker-compose.test.yml).
FROM python:3.12-slim

WORKDIR /app
COPY . /app

RUN pip install --no-cache-dir -r requirements-dev.txt

# Run the suite as a non-root user (Trivy DS-0002); it owns /app so pytest can
# write coverage reports (coverage.xml, htmlcov/) and its cache.
RUN useradd -r -u 10001 tester && chown -R tester /app
USER 10001

CMD ["pytest"]
