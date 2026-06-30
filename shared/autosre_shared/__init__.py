"""AutoSRE shared platform library.

One source of truth for observability, chaos, resilience, storage, and
cross-service clients used by the api, auth, and worker services.
"""

from .app import create_service_app
from .logging import configure_logging, get_logger
from .clients import ServiceClient, HTTPServiceClient
from .context import get_correlation_id, get_request_id
from .envcheck import validate_env

__all__ = [
    "create_service_app",
    "configure_logging",
    "get_logger",
    "ServiceClient",
    "HTTPServiceClient",
    "get_correlation_id",
    "get_request_id",
    "validate_env",
]
