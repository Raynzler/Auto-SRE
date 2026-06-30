"""Structured (JSON) logging shared by all AutoSRE services."""

import json
import logging
import sys

from .context import correlation_id_var, request_id_var


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": request_id_var.get(),
            "correlation_id": correlation_id_var.get(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        # Include any structured extras attached via logger.x(..., extra={...}).
        for key, value in getattr(record, "__dict__", {}).items():
            if key not in _RESERVED and not key.startswith("_"):
                payload.setdefault(key, value)
        return json.dumps(payload, default=str)


_RESERVED = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys()) | {
    "message",
    "asctime",
}


def configure_logging(service: str, level: int = logging.INFO) -> logging.Logger:
    """Install a JSON handler on the root logger and return the service logger."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
    return logging.getLogger(f"autosre.{service}")


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
