# Documentation

## Summary
This project implements a basic freight search management system. It adds a `FreightSearch` model, CRUD endpoints for freights and freight searches, and matching logic exposed via `GET /freight/{freight_id}/find_matches/`.

## How instructions were followed
- Implemented the `FreightSearch` model associated with users including optional constraints for price bounds, pickup/delivery codes, and date windows.
- CRUD endpoints for `Freight` and `FreightSearch`.
- Implemented `/freight/{freight_id}/find_matches/` which returns freight searches with index-friendly filtering, stable ordering, and pagination.
- Added indexes on searchable columns for scalability.
- Provided automated tests under `tests/` and standalone stress_test.py at the project root that create freight searches and verify matching behaviour.

## Data Model

**Matching semantics**
- **Route:** search matches if `pickup_code` is `NULL` **or** equals the freight’s `pickup_code`; same for `delivery_code`.
- **Price:** `min_price` `NULL` or `min_price <= freight.price`, and `max_price` `NULL` or `max_price >= freight.price`.
- **Dates:** the freight’s `pickup_date` lies within the search pickup window (if present), and `delivery_date` lies within the delivery window (if present).

**Pagination & ordering**
- `GET /freight/{id}/find_matches/?limit=…&offset=…`
- Stable ordering to ensure deterministic paging (no duplicates/skips across pages).

## Endpoints
```
GET /hello/
GET  /freights/
GET  /freight_searches/

POST /freights/
{
  "price": 300.0,
  "pickup_code": 10100,
  "delivery_code": 20100,
  "pickup_date": "2022-01-01",
  "delivery_date": "2022-01-02"
}

POST /freight_searches/
#all optional except user_id
{
  "user_id": 1,
  "pickup_code": 10100,
  "delivery_code": 20100,
  "min_price": 200,
  "max_price": 400,
  "pickup_date_from": "2021-12-30",
  "pickup_date_to": "2022-01-02",
  "delivery_date_from": "2022-01-01",
  "delivery_date_to": "2022-01-03"
}
```

GET example matching
`GET /freight/{freight_id}/find_matches/?limit=200&offset=0`

## Scalability
## Query Shape

- Route predicates use `IN ([value, NULL])` to stay index-friendly.
- Optional bounds keep “nullable means no constraint” semantics.

## Indexes

### Composite, Portable
- `(pickup_code, delivery_code)`

### Partial / Filtered
*(Supported by PostgreSQL and SQLite; ignored by MySQL)*
- `min_price WHERE min_price IS NOT NULL`
- `max_price WHERE max_price IS NOT NULL`
- `pickup_date_from WHERE pickup_date_from IS NOT NULL`
- `pickup_date_to WHERE pickup_date_to IS NOT NULL`
- `delivery_date_from WHERE delivery_date_from IS NOT NULL`
- `delivery_date_to WHERE delivery_date_to IS NOT NULL`

## Database Choice

- Works with any SQLAlchemy backend.
- For ≈1M+ searches, **PostgreSQL is recommended** (filtered indexes, stronger planner).
- **SQLite** is configured with **WAL** for better dev/test concurrency.

## Configuration
Set DATABASE_URL to select the backend
### SQLite (development)
`export DATABASE_URL="sqlite+aiosqlite:///./test.db"`
### Initialize tables + seed 
`python init_db.py`

## Running the application
```
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8000 --workers 1
```
With SQLite, keep --workers 1 to avoid write contention, with PostgreSQL, scale --workers as needed

## Running tests
### Test without uvicorn
Unit tests + Light stress test (seeds ~20k freight_searches and fires 500 concurrent in-process requests)
`PYTHONPATH=. pytest -v`

### Test with hitting uvicorn endpoint 1M requests
If you want to try high concurrency and 1M+ rows with low latency, use Postgres for this specific test start psql and run

Delete test.db test.db-shm test.db-wal

```Create db and user and grant privileges
CREATE ROLE fulltruck WITH LOGIN PASSWORD 'fulltruck2025';
CREATE DATABASE fulltruck OWNER fulltruck;
GRANT ALL PRIVILEGES ON DATABASE fulltruck TO fulltruck;
```
change the DATABASE_URL in database.py and run 
`export DATABASE_URL="postgresql+asyncpg://fulltruck:fulltruck2025@127.0.0.1/fulltruck"`

run to seed
`python init_db.py`

start uvicorn, this will fail 
`uvicorn server:app --host 0.0.0.0 --port 8000 --workers 8`
run the test
```
python stress_test.py \
  --rows 50000 \
  --batch 10000 \
  --requests 1000 \
  --concurrency 100 \
  --base-url http://127.0.0.1:8000
```

Without postgress simply start uvicorn with a single worker and run the test
start uvicorn
`uvicorn server:app --host 0.0.0.0 --port 8000 --workers 1`
run the test
```
python stress_test.py \
  --rows 50000 \
  --batch 10000 \
  --requests 1000 \
  --concurrency 100 \
  --base-url http://127.0.0.1:8000
```

## Notes
Seeding 1M rows is resource-intensive; use PostgreSQL on SSD and keep SQL echo off
Increase uvicorn workers and DB pool size with PostgreSQL as needed.
Re-running stress against the same DB increases row count: point to a separate DB or reset data
High CPU during seeding: increase --batch and ensure adequate DB resources

### clean postgress after each run 
psql "postgresql://fulltruck:fulltruck2025@127.0.0.1/fulltruck" \
  -c "TRUNCATE TABLE freight_searches RESTART IDENTITY;"

### seed again after truncate
`python init_db.py`