# tests/test_matching.py
import sys
from pathlib import Path
from contextlib import asynccontextmanager

import pytest
from httpx import ASGITransport, AsyncClient

sys.path.append(str(Path(__file__).resolve().parent.parent))
import server


@asynccontextmanager
async def lifespan(app):
    async with app.router.lifespan_context(app):
        yield


@pytest.mark.asyncio
async def test_match_found():
    async with lifespan(server.app):
        async with AsyncClient(transport=ASGITransport(app=server.app), base_url="http://testserver") as client:
            search = {
                "user_id": 1,
                "pickup_code": 10100,
                "delivery_code": 20100,
                "min_price": 200,
                "max_price": 350,
            }
            resp = await client.post("/freight_searches/", json=search)
            assert resp.status_code == 200
            search_id = resp.json()["id"]

            resp = await client.get("/freight/1/find_matches/")
            assert resp.status_code == 200
            matches = resp.json()
            assert any(m["id"] == search_id for m in matches)


@pytest.mark.asyncio
async def test_no_match():
    async with lifespan(server.app):
        async with AsyncClient(transport=ASGITransport(app=server.app), base_url="http://testserver") as client:
            search = {
                "user_id": 1,
                "pickup_code": 99999,
            }
            resp = await client.post("/freight_searches/", json=search)
            assert resp.status_code == 200

            resp = await client.get("/freight/1/find_matches/")
            assert resp.status_code == 200
            assert all(m.get("pickup_code") != 99999 for m in resp.json())