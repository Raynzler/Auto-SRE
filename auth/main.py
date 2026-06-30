"""AutoSRE Auth service.

Simulates token validation against a downstream identity provider that has
artificial latency. The downstream call is guarded by a circuit breaker, and
the service is rate limited. All platform concerns come from autosre_shared.
"""

import asyncio
import os

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field
from prometheus_client import Counter

from autosre_shared import create_service_app
from autosre_shared.resilience import get_or_create
from autosre_shared.resilience.circuit_breaker import BreakerState

# Artificial dependency latency for the simulated identity provider.
DEP_LATENCY = float(os.getenv("AUTH_DEP_LATENCY", "0.08"))
INVALID_TOKENS = {"", "invalid", "expired"}

auth_token_validations_total = Counter(
    "auth_token_validations_total", "Token validations by result", ["result"]
)


class TokenRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str = Field(min_length=1, max_length=4096)


def _identity_breaker():
    return get_or_create(
        "identity-provider", failure_threshold=5, recovery_timeout=20.0, success_threshold=2
    )


async def _validate_with_backend(token: str) -> bool:
    """Simulated downstream identity-provider call (guarded by a breaker)."""

    async def backend() -> bool:
        await asyncio.sleep(DEP_LATENCY)  # artificial dependency latency
        return token not in INVALID_TOKENS

    return await _identity_breaker().call(backend)


router = APIRouter(tags=["auth"])


@router.post("/validate")
async def validate(req: TokenRequest):
    valid = await _validate_with_backend(req.token)
    auth_token_validations_total.labels(result="valid" if valid else "invalid").inc()
    return {"valid": valid, "token": req.token}


async def _readiness():
    breaker = _identity_breaker()
    return {"ready": breaker.state != BreakerState.OPEN, "identity_breaker": breaker.state.value}


# Register the downstream breaker at import so it appears in /breaker/status.
_identity_breaker()

app = create_service_app(
    service_name="auth",
    title="AutoSRE Auth Service",
    enable_rate_limit=True,
    business_routers=[router],
    readiness_check=_readiness,
)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8001")))
