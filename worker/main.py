"""AutoSRE Worker service.

Runs a background job loop that simulates task execution and emits RED-style
job metrics. It is chaos-compatible: latency and error injection affect job
processing (via the shared chaos state), and CPU/memory chaos run in-process
through the shared chaos endpoints. Exposes /health, /ready, /metrics, /chaos.
"""

import asyncio
import os
import time

from prometheus_client import Counter, Histogram

from autosre_shared import create_service_app
from autosre_shared.storage import record_event, Source

WORKER_INTERVAL = float(os.getenv("WORKER_INTERVAL", "5"))
JOB_BASE_SECONDS = float(os.getenv("WORKER_JOB_SECONDS", "0.2"))

worker_jobs_processed_total = Counter(
    "worker_jobs_processed_total", "Background jobs processed", ["status"]
)
worker_job_duration_seconds = Histogram(
    "worker_job_duration_seconds",
    "Background job execution time in seconds",
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10),
)


async def _process_job(chaos) -> str:
    start = time.perf_counter()
    status = "success"
    try:
        # Chaos compatibility: latency + deterministic error injection.
        if chaos.state.latency_enabled and chaos.state.latency_seconds > 0:
            await asyncio.sleep(chaos.state.latency_seconds)
        if chaos.state.should_inject_error():
            raise RuntimeError("chaos: injected job failure")
        await asyncio.sleep(JOB_BASE_SECONDS)  # task execution simulation
    except Exception:
        status = "failed"
        record_event(Source.WORKER, "job_failed", service="worker")
    finally:
        worker_job_duration_seconds.observe(time.perf_counter() - start)
        worker_jobs_processed_total.labels(status=status).inc()
    return status


async def _job_loop(app):
    chaos = app.state.chaos
    logger = app.state.logger
    logger.info("worker loop started", extra={"interval_s": WORKER_INTERVAL})
    try:
        while True:
            await _process_job(chaos)
            await asyncio.sleep(WORKER_INTERVAL)
    except asyncio.CancelledError:
        logger.info("worker loop cancelled")
        raise


async def _startup(app):
    app.state.job_task = asyncio.create_task(_job_loop(app))


async def _shutdown(app):
    task = getattr(app.state, "job_task", None)
    if task is not None:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = create_service_app(
    service_name="worker",
    title="AutoSRE Worker Service",
    enable_rate_limit=False,  # background service, no external request traffic
    on_startup=_startup,
    on_shutdown=_shutdown,
)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8002")))
