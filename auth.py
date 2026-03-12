# ──────────────────────────────────────────────
# auth.py — JWT Authentication Logic
#
# This file handles:
# 1. Creating JWT tokens (like issuing OAuth tokens in MuleSoft)
# 2. Verifying JWT tokens (like API Manager policy checking tokens)
# 3. Password hashing (never store plain passwords!)
# ──────────────────────────────────────────────

from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# ── SECRET KEY ──────────────────────────────────
# In production: store this in environment variable!
# Like storing credentials in Anypoint Secrets Manager
SECRET_KEY  = "your-super-secret-key-change-in-production"
ALGORITHM   = "HS256"
TOKEN_EXPIRE_MINUTES = 60   # Token valid for 1 hour

# ── PASSWORD HASHING ──────────────────────────
# bcrypt hashes passwords so they're never stored plain
# Like encrypting credentials in MuleSoft Secure Properties
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ── BEARER TOKEN SCHEME ─────────────────────────
# Reads "Authorization: Bearer <token>" from request header
# Like API Manager reading the Authorization header
security = HTTPBearer()

def hash_password(plain_password: str) -> str:
    """
    Convert plain password → hashed password
    e.g. "mypassword" → "$2b$12$xxx..."
    NEVER store plain passwords in database!
    """
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Check if plain password matches stored hash
    Returns True if match, False if not
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_token(data: dict) -> str:
    """
    Create a JWT token containing user data.

    MuleSoft analogy:
    Like generating an OAuth2 access token —
    it contains user info and has an expiry time

    Example token payload:
    {
      "sub": "admin@company.com",  ← user identifier
      "exp": 1234567890            ← expiry timestamp
    }
    """
    payload    = data.copy()
    expiry     = datetime.utcnow() + timedelta(minutes=TOKEN_EXPIRE_MINUTES)
    payload.update({"exp": expiry})

    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token


def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    """
    Verify incoming JWT token on protected endpoints.

    FastAPI automatically calls this as a "dependency"
    on any endpoint that has:
        current_user = Depends(verify_token)
    """
    try:
        token   = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email   = payload.get("sub")

        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")

        return email    # Returns the logged-in user's email

    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Token is invalid or expired — please login again"
        )