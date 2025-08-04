# models.py
from sqlalchemy import Column, Date, Integer, String, Float, ForeignKey, Index, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    surname = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)

class Freight(Base):
    __tablename__ = "freights"

    id = Column(Integer, primary_key=True, index=True)
    price = Column(Float, nullable=False)
    pickup_code = Column(Integer, index=True, nullable=False)    # e.g. 10001
    delivery_code = Column(Integer, index=True, nullable=False)  # e.g. 20001
    pickup_date = Column(Date, nullable=False)
    delivery_date = Column(Date, nullable=False)


class FreightSearch(Base):
    __tablename__ = "freight_searches"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    min_price = Column(Float, nullable=True, index=True)
    max_price = Column(Float, nullable=True, index=True)
    pickup_code = Column(Integer, index=True, nullable=True)
    delivery_code = Column(Integer, index=True, nullable=True)
    pickup_date_from = Column(Date, nullable=True, index=True)
    pickup_date_to = Column(Date, nullable=True, index=True)
    delivery_date_from = Column(Date, nullable=True, index=True)
    delivery_date_to = Column(Date, nullable=True, index=True)

    # New: creation time for recency ordering (UTC on Postgres; SQLite uses local)
    created_at = Column(DateTime(timezone=True), nullable=False,
                        server_default=func.now(), index=True)

    user = relationship("User", backref="freight_searches")


# ──────────────────────────────────────────────────────────────────────────────
# Indexes & Portability Notes
# - Composite B-tree index (pickup_code, delivery_code) is portable across
#   PostgreSQL / MySQL / SQLite.
# - Partial (filtered) indexes are dialect-specific:
#     * PostgreSQL: supported (use postgresql_where=...)
#     * SQLite: supported (use sqlite_where=...) — handy for dev
#     * MySQL: NOT supported (these WHERE clauses are ignored);
#       rely on composite indexes + query shape, or generated columns/partitioning.
# For 1M+ rows, PostgreSQL is recommended for best plans and filtered indexes.
# ──────────────────────────────────────────────────────────────────────────────

# Route index: typically the strongest filter
Index("idx_fs_route", FreightSearch.pickup_code, FreightSearch.delivery_code)

# Partial indexes (no-op on MySQL)
Index(
    "idx_fs_min_price_not_null",
    FreightSearch.min_price,
    sqlite_where=FreightSearch.min_price.isnot(None),
    postgresql_where=FreightSearch.min_price.isnot(None),
)
Index(
    "idx_fs_max_price_not_null",
    FreightSearch.max_price,
    sqlite_where=FreightSearch.max_price.isnot(None),
    postgresql_where=FreightSearch.max_price.isnot(None),
)
Index(
    "idx_fs_pickup_from_not_null",
    FreightSearch.pickup_date_from,
    sqlite_where=FreightSearch.pickup_date_from.isnot(None),
    postgresql_where=FreightSearch.pickup_date_from.isnot(None),
)
Index(
    "idx_fs_pickup_to_not_null",
    FreightSearch.pickup_date_to,
    sqlite_where=FreightSearch.pickup_date_to.isnot(None),
    postgresql_where=FreightSearch.pickup_date_to.isnot(None),
)
Index(
    "idx_fs_delivery_from_not_null",
    FreightSearch.delivery_date_from,
    sqlite_where=FreightSearch.delivery_date_from.isnot(None),
    postgresql_where=FreightSearch.delivery_date_from.isnot(None),
)
Index(
    "idx_fs_delivery_to_not_null",
    FreightSearch.delivery_date_to,
    sqlite_where=FreightSearch.delivery_date_to.isnot(None),
    postgresql_where=FreightSearch.delivery_date_to.isnot(None),
)


class Test(Base):
    __tablename__ = "test"

    id = Column(Integer, primary_key=True, index=True)
    message = Column(String, index=True)
