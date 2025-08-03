from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.provider import APIKey

security = HTTPBearer()

# JWT settings for portal authentication
SECRET_KEY = settings.secret_key or "your-secret-key-here"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


async def get_current_api_key(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> APIKey:
    """
    Validate API key from Authorization header and check if it's active and not expired.
    """
    api_key_value = credentials.credentials

    # Find the API key in database
    result = await db.execute(select(APIKey).where(APIKey.api_key == api_key_value))
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key"
        )

    # Check if key is active
    if not api_key.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="API key is deactivated"
        )

    # Check if key is expired
    if api_key.expires_at and api_key.expires_at < datetime.now(
        api_key.expires_at.tzinfo
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="API key has expired"
        )

    return api_key


async def get_optional_api_key(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Optional[APIKey]:
    """
    Optional API key validation. Returns None if no key provided or invalid.
    """
    if not credentials:
        return None

    try:
        return await get_current_api_key(credentials, db)
    except HTTPException:
        return None


# Portal Authentication Functions
async def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token for portal login"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def verify_token(token: str) -> Optional[str]:
    """Verify JWT token and return username if valid"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        return username
    except JWTError:
        return None


async def authenticate_portal_api_key(api_key: str, db: AsyncSession) -> bool:
    """Authenticate API key against database for portal access"""
    result = await db.execute(
        select(APIKey).where(APIKey.api_key == api_key, APIKey.is_active.is_(True))
    )
    key_record = result.scalar_one_or_none()

    if not key_record:
        return False

    # Check if key is expired
    if key_record.expires_at and key_record.expires_at < datetime.utcnow():
        return False

    return True


async def get_current_portal_user(
    request: Request, db: AsyncSession = Depends(get_db)
) -> str:
    """Get current authenticated portal user"""
    # Try to get token from Authorization header first
    auth_header = request.headers.get("Authorization")
    token = None

    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]

    # If no token in header, check for token in cookies (for browser requests)
    if not token:
        token = request.cookies.get("portal_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    username = await verify_token(token)

    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return username


async def login_for_access_token(api_key: str, db: AsyncSession) -> dict:
    """Login and return access token for portal"""
    if not await authenticate_portal_api_key(api_key, db):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = await create_access_token(
        data={"sub": f"portal_user_{api_key[:20]}"}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}
