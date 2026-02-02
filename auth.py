from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from database import get_db, User
import os

# --- Configuration ---
# In production, use a secure random secret key!
SECRET_KEY = os.getenv("SECRET_KEY", "super_secret_key_for_dev_only_12345")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 Days

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/token")

import hashlib

# --- Password Utils ---
def verify_password(plain_password, hashed_password):
    # Fix: Pre-hash with SHA-256 to ensure input is always 64 chars (safe for bcrypt)
    # This solves the 72-byte limit and Unicode issues.
    safe_password = hashlib.sha256(plain_password.encode('utf-8')).hexdigest()
    return pwd_context.verify(safe_password, hashed_password)

def get_password_hash(password):
    # Fix: Pre-hash with SHA-256
    safe_password = hashlib.sha256(password.encode('utf-8')).hexdigest()
    return pwd_context.hash(safe_password)

# --- Token Utils ---
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# --- Dependency: Current User ---
async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user
