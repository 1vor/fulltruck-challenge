# tests/test_keyset_pagination.py
import pytest
from httpx import ASGITransport, AsyncClient
from contextlib import asynccontextmanager
import server

@asynccontextmanager
async def lifespan(app):
    async with app.router.lifespan_context(app):
        yield

@pytest.mark.asyncio
async def test_keyset_headers_present():
    async with lifespan(server.app):
        async with AsyncClient(transport=ASGITransport(app=server.app), base_url="http://testserver") as client:
            r = await client.post("/freight_searches/", json={"user_id": 1, "pickup_code": 10100, "delivery_code": 20100})
            assert r.status_code == 200
            r = await client.get("/freight/1/find_matches/?limit=1")
            assert r.status_code == 200
            assert "X-Next-Before-Ts" in r.headers
            assert "X-Next-Before-Id" in r.headers
