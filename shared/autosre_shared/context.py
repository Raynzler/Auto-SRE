"""Per-request context: request IDs and correlation IDs.

Stored in contextvars so they are available to the logger and to downstream
service calls without threading them through every function signature.
"""

import contextvars
from uuid import uuid4

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")
correlation_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "correlation_id", default="-"
)


def new_id() -> str:
    return uuid4().hex


def get_request_id() -> str:
    return request_id_var.get()


def get_correlation_id() -> str:
    return correlation_id_var.get()


def propagation_headers() -> dict[str, str]:
    """Headers to carry trace context to a downstream service.

    Propagates the correlation ID so a whole request chain shares one id; each
    hop still gets its own request ID generated on arrival.
    """
    cid = correlation_id_var.get()
    return {"X-Correlation-ID": cid} if cid and cid != "-" else {}
