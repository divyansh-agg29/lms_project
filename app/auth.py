from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import secrets, hashlib

from .config import settings
from .database import get_db
from . import crud
from .models import Role


pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

def create_access_token(data: dict, expires_delta: timedelta|None = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({'exp':expire})
    return jwt.encode(to_encode, settings.SECRET_KEY,algorithm=settings.ALGORITHM)

def decode_token(token: str):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None
    
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Token")
    
    email: str = payload.get('sub')
    if email is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Token")
    
    user = crud.get_employee_by_email(db, email)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive or not found")
    return user

def require_role(allowed_roles: List[Role]):
    def role_checker(current_user = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail = "You do not have permission for this action")
        
        return current_user
    return role_checker




def hash_refresh_token(token: str) -> str:
    """Hash a refresh token for safe DB storage."""
    return hashlib.sha256(token.encode()).hexdigest()

def create_and_store_refresh_token(db: Session, user_id: int) -> str:
    """Generate, hash, and store a refresh token in DB; return the raw token."""
    raw_token = secrets.token_urlsafe(32)
    token_hash = hash_refresh_token(raw_token)
    expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    crud.create_refresh_token(db, user_id=user_id, token_hash=token_hash, expires_at=expires_at)
    return raw_token

def verify_refresh_token(db: Session, raw_token: str):
    """Check refresh token validity and return user if valid, else None."""
    token_hash = hash_refresh_token(raw_token)
    rt = crud.get_refresh_token_by_hash(db, token_hash)
    if not rt or rt.expires_at < datetime.utcnow():
        return None
    return rt.user

def revoke_refresh_token(db: Session, raw_token: str) -> bool:
    """Revoke (delete) a refresh token from DB."""
    token_hash = hash_refresh_token(raw_token)
    return crud.revoke_refresh_token(db, token_hash)