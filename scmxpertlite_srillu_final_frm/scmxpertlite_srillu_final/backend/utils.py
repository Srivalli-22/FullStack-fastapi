from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends, HTTPException

from config import JWT_SECRET
from mongo_db import get_user_by_id


# ============================================================
# PASSWORD HASHING (argon2 + bcrypt fallback)
# ============================================================

pwd_context = CryptContext(
    schemes=['argon2', 'bcrypt'],
    deprecated='auto'
)

def get_password_hash(password: str):
    """Hash password with argon2 (bcrypt fallback)"""
    password = password[:72] if password else password
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str):
    """Verify password"""
    plain_password = plain_password[:72] if plain_password else plain_password
    return pwd_context.verify(plain_password, hashed_password)


# ============================================================
# JWT TOKEN CREATION & DECODING
# ============================================================

def create_access_token(data: dict, expires_minutes: int = 60):
    """Create JWT Access Token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm="HS256")


def decode_access_token(token: str):
    """Decode token. Return payload if valid, else None."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except JWTError:
        return None


# ============================================================
# HTTP BEARER AUTH — FIXES SWAGGER AUTHORIZE POPUP
# ============================================================

security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Validate JWT token using HTTP Bearer scheme and load the user from MongoDB.
    """
    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated or token expired",
        )

    user_id = payload.get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    # Normalize shape for downstream code
    return {
        "id": user["id"],
        "email": user.get("email"),
        "full_name": user.get("full_name"),
        "role": user.get("role", "shipment_manager"),
        "sub": user.get("email"),
    }
