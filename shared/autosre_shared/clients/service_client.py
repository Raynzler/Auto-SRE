"""Cross-service communication abstraction.

Services talk to each other through the ServiceClient interface, never a
concrete transport. Today: HTTP (HTTPServiceClient). Because callers depend on
the interface, a future transport (a queue, gRPC, or a Redis-backed RPC) can be
introduced by adding a new implementation — no business-logic change. Tests
inject a fake client implementing the same interface.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional

import httpx

from ..context import propagation_headers


class ServiceClient(ABC):
    @abstractmethod
    async def get_json(self, path: str, **kwargs) -> Any: ...

    @abstractmethod
    async def post_json(self, path: str, json: Optional[dict] = None, **kwargs) -> Any: ...

    async def aclose(self) -> None:  # optional override
        return None


class HTTPServiceClient(ServiceClient):
    def __init__(
        self, base_url: str, timeout: float = 5.0, client: Optional[httpx.AsyncClient] = None
    ):
        self.base_url = base_url.rstrip("/")
        self._client = client or httpx.AsyncClient(timeout=timeout)

    async def get_json(self, path: str, **kwargs) -> Any:
        kwargs["headers"] = {**propagation_headers(), **kwargs.get("headers", {})}
        resp = await self._client.get(self.base_url + path, **kwargs)
        resp.raise_for_status()
        return resp.json()

    async def post_json(self, path: str, json: Optional[dict] = None, **kwargs) -> Any:
        kwargs["headers"] = {**propagation_headers(), **kwargs.get("headers", {})}
        resp = await self._client.post(self.base_url + path, json=json, **kwargs)
        resp.raise_for_status()
        return resp.json()

    async def aclose(self) -> None:
        await self._client.aclose()
