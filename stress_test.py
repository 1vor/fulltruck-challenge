# stress_test.py
import asyncio
import random
import time
import statistics
import argparse
from datetime import date, timedelta

import httpx

from server import app
from database import AsyncSessionLocal
from models import FreightSearch
from sqlalchemy import insert

def pct(values, p):
    if not values:
        return 0.0
    idx = max(0, min(len(values)-1, int(len(values) * p)))
    return sorted(values)[idx]

async def seed_searches(total_rows: int, batch_size: int = 5000):
    """Bulk-insert many FreightSearch rows quickly."""
    print(f"[seed] Seeding {total_rows:,} freight_searches in batches of {batch_size}...")
    start = time.perf_counter()
    lanes = [(10100, 20100), (10100, 20200), (10200, 20300), (10300, 20400)]
    base_pickup = date(2022, 1, 1)
    base_delivery = date(2022, 1, 2)

    inserted = 0
    async with AsyncSessionLocal() as session:
        while inserted < total_rows:
            rows = min(batch_size, total_rows - inserted)
            payload = []
            for _ in range(rows):
                # Some rows with exact lanes, some with no constraints
                if random.random() < 0.8:
                    pickup_code, delivery_code = random.choice(lanes)
                else:
                    pickup_code = None
                    delivery_code = None

                # Price bounds with occasional NULLs
                if random.random() < 0.9:
                    min_price = random.choice([None, 150.0, 200.0, 250.0])
                    max_price = random.choice([None, 350.0, 400.0, 450.0, 600.0])
                    if min_price and max_price and max_price < min_price:
                        min_price, max_price = max_price, min_price
                else:
                    min_price = None
                    max_price = None

                # Pickup window with occasional NULLs
                if random.random() < 0.85:
                    p_from = base_pickup - timedelta(days=random.randint(0, 3))
                    p_to   = base_pickup + timedelta(days=random.randint(0, 3))
                    if p_to < p_from:
                        p_from, p_to = p_to, p_from
                else:
                    p_from = None
                    p_to = None

                # Delivery window with occasional NULLs
                if random.random() < 0.85:
                    d_from = base_delivery - timedelta(days=random.randint(0, 3))
                    d_to   = base_delivery + timedelta(days=random.randint(0, 3))
                    if d_to < d_from:
                        d_from, d_to = d_to, d_from
                else:
                    d_from = None
                    d_to = None

                payload.append({
                    "user_id": 1,  # assumes sample user exists
                    "min_price": min_price,
                    "max_price": max_price,
                    "pickup_code": pickup_code,
                    "delivery_code": delivery_code,
                    "pickup_date_from": p_from,
                    "pickup_date_to": p_to,
                    "delivery_date_from": d_from,
                    "delivery_date_to": d_to,
                })

            await session.execute(insert(FreightSearch), payload)
            await session.commit()
            inserted += rows
            if inserted % (batch_size * 5) == 0 or inserted == total_rows:
                print(f"[seed] Inserted {inserted:,}/{total_rows:,}")

    dur = time.perf_counter() - start
    print(f"[seed] Done in {dur:.1f}s (~{total_rows/dur:,.0f} rows/s)")

async def ensure_freight_exists(client):
    """Make sure /freights contains at least one freight (id=1)."""
    resp = await client.get("/freights/")
    resp.raise_for_status()
    data = resp.json()
    if not data:
        payload = {
            "price": 300.0,
            "pickup_code": 10100,
            "delivery_code": 20100,
            "pickup_date": "2022-01-01",
            "delivery_date": "2022-01-02",
        }
        r2 = await client.post("/freights/", json=payload)
        r2.raise_for_status()
        print("[seed] Created default freight:", r2.json())

async def one_request(client, freight_id, limit, stats):
    t0 = time.perf_counter()
    resp = await client.get(f"/freight/{freight_id}/find_matches/?limit={limit}")
    dt = time.perf_counter() - t0
    if resp.status_code == 200:
        stats.append(dt)

async def _drive(client, requests, concurrency, freight_id, limit):
    stats = []
    sem = asyncio.Semaphore(concurrency)

    async def worker():
        async with sem:
            await one_request(client, freight_id, limit, stats)

    t0 = time.perf_counter()
    await asyncio.gather(*(worker() for _ in range(requests)))
    dur = time.perf_counter() - t0

    if stats:
        avg = statistics.mean(stats)
        p50 = pct(stats, 0.50)
        p90 = pct(stats, 0.90)
        p95 = pct(stats, 0.95)
        p99 = pct(stats, 0.99)
    else:
        avg = p50 = p90 = p95 = p99 = 0.0

    print(f"[load] requests={requests:,} concurrency={concurrency} time={dur:.2f}s "
          f"rps={requests/dur:,.0f}")
    print(f"[load] latency avg={avg*1000:.1f}ms p50={p50*1000:.1f}ms p90={p90*1000:.1f}ms "
          f"p95={p95*1000:.1f}ms p99={p99*1000:.1f}ms")

async def run_load(base_url, requests, concurrency, freight_id=1, limit=200, inprocess=False):
    if inprocess:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            await ensure_freight_exists(client)
            await _drive(client, requests, concurrency, freight_id, limit)
    else:
        async with httpx.AsyncClient(base_url=base_url, timeout=30) as client:
            await ensure_freight_exists(client)
            await _drive(client, requests, concurrency, freight_id, limit)

async def main():
    parser = argparse.ArgumentParser(description="Seed and stress-test /find_matches")
    parser.add_argument("--rows", type=int, default=200_000, help="rows to seed in freight_searches")
    parser.add_argument("--batch", type=int, default=10_000, help="insert batch size")
    parser.add_argument("--requests", type=int, default=10_000, help="total requests")
    parser.add_argument("--concurrency", type=int, default=200, help="concurrent requests")
    parser.add_argument("--freight-id", type=int, default=1)
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--base-url", type=str, default="http://127.0.0.1:8000")
    parser.add_argument("--inprocess", action="store_true", help="use ASGITransport (no external server)")
    args = parser.parse_args()

    # Seed first
    await seed_searches(args.rows, args.batch)

    # Load test
    await run_load(
        base_url=args.base_url,
        requests=args.requests,
        concurrency=args.concurrency,
        freight_id=args.freight_id,
        limit=args.limit,
        inprocess=args.inprocess,
    )

if __name__ == "__main__":
    asyncio.run(main())
