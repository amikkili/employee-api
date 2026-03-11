import os
import asyncpg

DATABASE_URL = os.getenv("DATABASE_URL")

# Global pool — lives here, accessed via get_pool()
_db_pool = None


async def connect_db():
    global _db_pool
    _db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10)
    print("Connected to PostgreSQL!")


async def disconnect_db():
    global _db_pool
    if _db_pool:
        await _db_pool.close()
        print("Disconnected from PostgreSQL")


def get_pool():
    """
    Always returns current pool reference.
    Fix: main.py calls get_pool() at request time
            instead of importing db_pool at startup time
    """
    return _db_pool


async def create_tables():
    async with _db_pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS employees (
                id         SERIAL PRIMARY KEY,
                name       VARCHAR(100) NOT NULL,
                role       VARCHAR(100) NOT NULL,
                department VARCHAR(100) NOT NULL,
                salary     NUMERIC(10,2) NOT NULL DEFAULT 0,
                status     VARCHAR(50)  NOT NULL DEFAULT 'Active',
                email      VARCHAR(150) NOT NULL,
                joined     VARCHAR(20)
            );
        """)

        count = await conn.fetchval("SELECT COUNT(*) FROM employees")
        if count == 0:
            print("Seeding initial data...")
            await conn.executemany("""
                INSERT INTO employees (name, role, department, salary, status, email, joined)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, [
                ("Sarah Mitchell", "Senior Developer",  "Engineering", 85000, "Active",   "sarah@company.com",  "2020-03-15"),
                ("James Okafor",   "MuleSoft Architect", "Integration", 95000, "Active",   "james@company.com",  "2019-07-22"),
                ("Priya Sharma",   "Data Analyst",       "Analytics",   72000, "Active",   "priya@company.com",  "2021-01-10"),
                ("Tom Henderson",  "Product Manager",    "Product",     90000, "On Leave", "tom@company.com",    "2018-11-05"),
                ("Aisha Patel",    "UX Designer",        "Design",      78000, "Active",   "aisha@company.com",  "2022-04-18"),
            ])
            print("Seed data inserted!")

        print("Tables ready!")