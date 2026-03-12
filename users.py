# ──────────────────────────────────────────────
# users.py — User Database Operations
#
# Handles creating and finding users in PostgreSQL
# MuleSoft analogy: Like your DB connector SELECT/INSERT
# but specifically for the "users" table
# ──────────────────────────────────────────────

from database import get_pool
from auth import hash_password

async def create_users_table():
    """
    Create users table in PostgreSQL.
    Called on app startup — just like employees table.

    Table structure:
    ┌─────────────────────────────────────-┐
    │ id       → Auto-increment primary key│
    │ email    → Login username (unique)   │
    │ password → Bcrypt hashed password    │
    │ name     → Display name              │
    └─────────────────────────────────────-┘
    """
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id       SERIAL PRIMARY KEY,
                email    VARCHAR(150) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                name     VARCHAR(100) NOT NULL
            );
        """)

        # Create a default admin user if no users exist
        # MuleSoft analogy: Like seeding default credentials
        count = await conn.fetchval("SELECT COUNT(*) FROM users")
        if count == 0:
            print("Creating default admin user...")
            await conn.execute("""
                INSERT INTO users (email, password, name)
                VALUES ($1, $2, $3)
            """,
                "admin@company.com",
                hash_password("admin123"),
                "Admin User"
            )
            print("Default admin created: admin@company.com / admin123")

        print("Users table ready!")


async def find_user_by_email(email: str):
    """
    Find a user by email address.
    MuleSoft analogy: SELECT * FROM users WHERE email = :email

    Returns user dict if found, None if not found.
    """
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM users WHERE email = $1", email
        )
        return dict(row) if row else None


async def create_user(email: str, password: str, name: str):
    """
    Create a new user in the database.
    MuleSoft analogy: INSERT INTO users (email, password, name) VALUES (...)

    Password is hashed before storing — never stored plain!
    """
    pool = get_pool()
    async with pool.acquire() as conn:

        # Check if email already exists
        existing = await conn.fetchrow(
            "SELECT id FROM users WHERE email = $1", email
        )
        if existing:
            return None     # Email already taken

        row = await conn.fetchrow("""
            INSERT INTO users (email, password, name)
            VALUES ($1, $2, $3)
            RETURNING id, email, name
        """,
            email,
            hash_password(password),
            name
        )
        return dict(row)