# server.py
from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI, Depends, HTTPException, Query, Response
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import or_, and_
from database import AsyncSessionLocal, engine, Base, get_db
from models import Freight, Test, User, FreightSearch
from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, field_validator


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables + indexes
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(lifespan=lifespan)


class FreightBase(BaseModel):
    price: float
    pickup_code: int
    delivery_code: int
    pickup_date: date
    delivery_date: date


class FreightCreate(FreightBase):
    pass


class FreightResponse(FreightBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class FreightSearchBase(BaseModel):
    user_id: int
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    pickup_code: Optional[int] = None
    delivery_code: Optional[int] = None
    pickup_date_from: Optional[date] = None
    pickup_date_to: Optional[date] = None
    delivery_date_from: Optional[date] = None
    delivery_date_to: Optional[date] = None

    # Light validation to catch inverted ranges early
    @field_validator("max_price")
    @classmethod
    def _price_bounds(cls, v, info):
        min_v = info.data.get("min_price")
        if v is not None and min_v is not None and v < min_v:
            raise ValueError("max_price must be >= min_price")
        return v

    @field_validator("pickup_date_to")
    @classmethod
    def _pickup_window(cls, v, info):
        f = info.data.get("pickup_date_from")
        if v is not None and f is not None and v < f:
            raise ValueError("pickup_date_to must be >= pickup_date_from")
        return v

    @field_validator("delivery_date_to")
    @classmethod
    def _delivery_window(cls, v, info):
        f = info.data.get("delivery_date_from")
        if v is not None and f is not None and v < f:
            raise ValueError("delivery_date_to must be >= delivery_date_from")
        return v


class FreightSearchCreate(FreightSearchBase):
    pass


class FreightSearchResponse(FreightSearchBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


@app.get("/hello/")
async def get_hello(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Test))
    test_record = result.scalars().first()
    if not test_record:
        raise HTTPException(status_code=404, detail="No test record found")
    return {"message": test_record.message}


@app.post("/freights/", response_model=FreightResponse)
async def create_freight(freight: FreightCreate, db: AsyncSession = Depends(get_db)):
    freight_obj = Freight(**freight.model_dump())
    db.add(freight_obj)
    await db.commit()
    await db.refresh(freight_obj)
    return freight_obj


@app.get("/freights/", response_model=List[FreightResponse])
async def list_freights(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Freight))
    return result.scalars().all()


@app.post("/freight_searches/", response_model=FreightSearchResponse)
async def create_freight_search(search: FreightSearchCreate, db: AsyncSession = Depends(get_db)):
    user = await db.get(User, search.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    search_obj = FreightSearch(**search.model_dump())
    db.add(search_obj)
    await db.commit()
    await db.refresh(search_obj)
    return search_obj


@app.get("/freight_searches/", response_model=List[FreightSearchResponse])
async def list_freight_searches(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(FreightSearch))
    return result.scalars().all()


@app.get("/freight/{freight_id}/find_matches/", response_model=List[FreightSearchResponse])
async def find_matches(
    freight_id: int,
    db: AsyncSession = Depends(get_db),
    response: Response = None,
    limit: int = Query(200, ge=1, le=1000),
    # OFFSET is still supported, but keyset is preferred for deep paging
    offset: int = Query(0, ge=0),
    # Keyset cursor: fetch rows BEFORE this (created_at, id) pair
    before_ts: Optional[datetime] = Query(None, description="ISO timestamp cursor for keyset paging"),
    before_id: Optional[int] = Query(None, description="ID cursor for keyset paging"),
):
    freight_obj = await db.get(Freight, freight_id)
    if not freight_obj:
        raise HTTPException(status_code=404, detail="Freight not found")

    # Route: IN ([value, NULL]) is a micro-optimization vs chained ORs
    route_conds = [
        FreightSearch.pickup_code.in_([freight_obj.pickup_code, None]),
        FreightSearch.delivery_code.in_([freight_obj.delivery_code, None]),
    ]

    # Price & date bounds: keep nullable means "no constraint" semantics
    price_conds = [
        or_(FreightSearch.min_price.is_(None), FreightSearch.min_price <= freight_obj.price),
        or_(FreightSearch.max_price.is_(None), FreightSearch.max_price >= freight_obj.price),
    ]
    pickup_conds = [
        or_(FreightSearch.pickup_date_from.is_(None), FreightSearch.pickup_date_from <= freight_obj.pickup_date),
        or_(FreightSearch.pickup_date_to.is_(None),   FreightSearch.pickup_date_to   >= freight_obj.pickup_date),
    ]
    delivery_conds = [
        or_(FreightSearch.delivery_date_from.is_(None), FreightSearch.delivery_date_from <= freight_obj.delivery_date),
        or_(FreightSearch.delivery_date_to.is_(None),   FreightSearch.delivery_date_to   >= freight_obj.delivery_date),
    ]

    conds = [*route_conds, *price_conds, *pickup_conds, *delivery_conds]

    # Keyset predicate: (created_at, id) < (before_ts, before_id) in DESC order
    # i.e., earlier than the last row from previous page
    if before_ts is not None and before_id is not None:
        conds.append(
            or_(
                FreightSearch.created_at < before_ts,
                and_(FreightSearch.created_at == before_ts, FreightSearch.id < before_id),
            )
        )

    base = select(FreightSearch).where(*conds)

    query = (
        base.order_by(FreightSearch.created_at.desc(), FreightSearch.id.desc())
            .limit(limit)
            .offset(offset)  # for compatibility; prefer keyset for deep pages
    )

    result = await db.execute(query)
    rows = result.scalars().all()

    # Expose next-keyset cursor via headers if page is full
    if response is not None and len(rows) == limit:
        last = rows[-1]
        # Safe for query params; ISO 8601 plus integer id
        response.headers["X-Next-Before-Ts"] = last.created_at.isoformat()
        response.headers["X-Next-Before-Id"] = str(last.id)

    return rows


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
