"""AutoSRE API service.

Business endpoints for orders. Validates tokens by calling the Auth service
through the shared ServiceClient abstraction, guarded by a circuit breaker.
All platform concerns (RED metrics, chaos, rate limiting, health/ready/metrics,
failure persistence) come from autosre_shared.
"""

import asyncio
import os
import uuid
from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from autosre_shared import create_service_app, HTTPServiceClient, ServiceClient
from autosre_shared.resilience import get_or_create
from autosre_shared.resilience.circuit_breaker import BreakerState, CircuitBreakerOpenError

# Cross-service dependency (HTTP today; swappable behind ServiceClient).
AUTH_URL = os.getenv("AUTH_URL", "http://auth:8001")
auth_client: ServiceClient = HTTPServiceClient(AUTH_URL)


class OrderRequest(BaseModel):
    # Strict input validation: reject unknown fields and out-of-range values.
    model_config = ConfigDict(extra="forbid")
    item: str = Field(min_length=1, max_length=100)
    quantity: int = Field(gt=0, le=1000)


class OrderResponse(BaseModel):
    order_id: str
    status: str
    item: str
    quantity: int


def _auth_breaker():
    return get_or_create("auth", failure_threshold=5, recovery_timeout=30.0, success_threshold=2)


router = APIRouter(tags=["orders"])


@router.post("/orders", response_model=OrderResponse)
async def create_order(order: OrderRequest, authorization: Optional[str] = Header(default=None)):
    token = (authorization or "").removeprefix("Bearer ").strip() or "demo-token"
    breaker = _auth_breaker()
    try:
        result = await breaker.call(auth_client.post_json, "/validate", json={"token": token})
    except CircuitBreakerOpenError:
        raise  # -> 503 via the shared exception handler
    except Exception:
        raise HTTPException(status_code=502, detail="auth dependency unavailable")

    if not result.get("valid"):
        raise HTTPException(status_code=401, detail="invalid token")

    order_id = f"order_{uuid.uuid4().hex[:8]}"
    await asyncio.sleep(0.05)
    return OrderResponse(
        order_id=order_id, status="created", item=order.item, quantity=order.quantity
    )


async def _readiness():
    # Degraded (not ready) when the auth dependency's breaker is open.
    breaker = _auth_breaker()
    return {"ready": breaker.state != BreakerState.OPEN, "auth_breaker": breaker.state.value}


async def _shutdown(_app):
    await auth_client.aclose()


# Register the auth breaker at import so it appears in /breaker/status.
_auth_breaker()

app = create_service_app(
    service_name="api",
    title="AutoSRE API Service",
    business_routers=[router],
    readiness_check=_readiness,
    on_shutdown=_shutdown,
)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
