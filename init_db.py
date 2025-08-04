# init_db.py
import asyncio
from datetime import date
from sqlalchemy import text, select
from database import engine, AsyncSessionLocal, Base
from models import Test

async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def seed_users_and_freights(session):
    # Detect dialect: 'sqlite' or 'postgresql'
    dialect = session.bind.dialect.name

    if dialect == "sqlite":
        # Users (email is UNIQUE) -> ignore duplicates
        await session.execute(text("""
            INSERT OR IGNORE INTO users (name, surname, email) VALUES
            ('Alice','Rossi','alice.rossi@example.com'),
            ('Bob','Bianchi','bob.bianchi@example.com')
        """))

        # Create a unique index so our demo freight rows stay idempotent
        await session.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS ux_freights_seed
            ON freights (price, pickup_code, delivery_code, pickup_date, delivery_date)
        """))

        await session.execute(text("""
            INSERT OR IGNORE INTO freights (price, pickup_code, delivery_code, pickup_date, delivery_date) VALUES
            (300.0,10100,20100,'2022-01-01','2022-01-02'),
            (450.5,10100,20200,'2022-01-02','2022-01-03'),
            (500.0,10200,20300,'2022-01-03','2022-01-04')
        """))

    elif dialect == "postgresql":
        # Users (email is UNIQUE)
        await session.execute(text("""
            INSERT INTO users (name, surname, email) VALUES
            ('Alice','Rossi','alice.rossi@example.com'),
            ('Bob','Bianchi','bob.bianchi@example.com')
            ON CONFLICT (email) DO NOTHING
        """))

        # Create a unique index once for the demo freight seed
        await session.execute(text("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_indexes
                    WHERE schemaname = 'public' AND indexname = 'ux_freights_seed'
                ) THEN
                    CREATE UNIQUE INDEX ux_freights_seed
                    ON freights (price, pickup_code, delivery_code, pickup_date, delivery_date);
                END IF;
            END;
            $$;
        """))

        await session.execute(text("""
            INSERT INTO freights (price, pickup_code, delivery_code, pickup_date, delivery_date) VALUES
            (300.0,10100,20100,'2022-01-01','2022-01-02'),
            (450.5,10100,20200,'2022-01-02','2022-01-03'),
            (500.0,10200,20300,'2022-01-03','2022-01-04')
            ON CONFLICT DO NOTHING
        """))
    else:
        # Fallback: try a simple "insert if not exists" approach for other DBs
        # Users
        await session.execute(text("""
            INSERT INTO users (name, surname, email)
            SELECT 'Alice','Rossi','alice.rossi@example.com'
            WHERE NOT EXISTS (SELECT 1 FROM users WHERE email='alice.rossi@example.com')
        """))
        await session.execute(text("""
            INSERT INTO users (name, surname, email)
            SELECT 'Bob','Bianchi','bob.bianchi@example.com'
            WHERE NOT EXISTS (SELECT 1 FROM users WHERE email='bob.bianchi@example.com')
        """))
        # Freights (may duplicate over many runs without a unique key)
        await session.execute(text("""
            INSERT INTO freights (price, pickup_code, delivery_code, pickup_date, delivery_date)
            SELECT 300.0,10100,20100,'2022-01-01','2022-01-02'
            WHERE NOT EXISTS (
                SELECT 1 FROM freights
                WHERE price=300.0 AND pickup_code=10100 AND delivery_code=20100
                  AND pickup_date='2022-01-01' AND delivery_date='2022-01-02'
            )
        """))
        await session.execute(text("""
            INSERT INTO freights (price, pickup_code, delivery_code, pickup_date, delivery_date)
            SELECT 450.5,10100,20200,'2022-01-02','2022-01-03'
            WHERE NOT EXISTS (
                SELECT 1 FROM freights
                WHERE price=450.5 AND pickup_code=10100 AND delivery_code=20200
                  AND pickup_date='2022-01-02' AND delivery_date='2022-01-03'
            )
        """))
        await session.execute(text("""
            INSERT INTO freights (price, pickup_code, delivery_code, pickup_date, delivery_date)
            SELECT 500.0,10200,20300,'2022-01-03','2022-01-04'
            WHERE NOT EXISTS (
                SELECT 1 FROM freights
                WHERE price=500.0 AND pickup_code=10200 AND delivery_code=20300
                  AND pickup_date='2022-01-03' AND delivery_date='2022-01-04'
            )
        """))

async def seed_test_message(session):
    # Ensure there's at least one Test row for /hello
    res = await session.execute(select(Test).limit(1))
    if not res.scalars().first():
        await session.execute(text("INSERT INTO test (message) VALUES ('Hello World')"))

async def main():
    await create_tables()
    async with AsyncSessionLocal() as session:
        await seed_users_and_freights(session)
        await seed_test_message(session)
        await session.commit()
    print("init_db: tables created and seed data ensured.")

if __name__ == "__main__":
    asyncio.run(main())
