# database.py
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import event

#sqlite
# DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./test.db")

#postgres
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://fulltruck:fulltruck2025@127.0.0.1/fulltruck")

engine = create_async_engine(
    DATABASE_URL,
    echo=False,         # set True only when debugging
    future=True,
    pool_pre_ping=True,
)

# SQLite dev-only pragmas to behave better with concurrency under async tests
if DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine.sync_engine, "connect")
    def _sqlite_pragmas(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA synchronous=NORMAL;")
        finally:
            cursor.close()

AsyncSessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession,
)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
