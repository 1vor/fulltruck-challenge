# tests/test_stress_smoke.py
import asyncio
import pytest
from httpx import ASGITransport, AsyncClient

from server import app
from database import AsyncSessionLocal
from models import FreightSearch
from sqlalchemy import insert

@pytest.mark.stress
@pytest.mark.asyncio
async def test_stress_smoke():
    #Seed ~20k rows and do 500 requests in-process, not a heavy benchmark is just a guard against regressions
    #Sed a modest number quickly
    async with AsyncSessionLocal() as session:
        rows = []
        for i in range(20_000):  # keep small for CI
            rows.append({
                "user_id": 1,
                "min_price": None if i % 3 else 200.0,
                "max_price": None if i % 5 else 400.0,
                "pickup_code": 10100 if i % 2 == 0 else None,
                "delivery_code": 20100 if i % 4 == 0 else None,
                "pickup_date_from": None,
                "pickup_date_to": None,
                "delivery_date_from": None,
                "delivery_date_to": None,
            })
        await session.execute(insert(FreightSearch), rows)
        await session.commit()

    #Drive 500 requests concurrently
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # create freight if missing
        resp = await client.get("/freights/")
        if not resp.json():
            await client.post("/freights/", json={
                "price": 300.0,
                "pickup_code": 10100,
                "delivery_code": 20100,
                "pickup_date": "2022-01-01",
                "delivery_date": "2022-01-02"
            })

        async def call():
            r = await client.get("/freight/1/find_matches/?limit=200")
            assert r.status_code == 200

        await asyncio.gather(*(call() for _ in range(500)))
