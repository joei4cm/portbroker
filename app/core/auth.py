from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from typing import Optional

from app.core.database import get_db
from app.models.provider import APIKey

security = HTTPBearer()


async def get_current_api_key(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
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
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    # Check if key is active
    if not api_key.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is deactivated"
        )
    
    # Check if key is expired
    if api_key.expires_at and api_key.expires_at < datetime.now(api_key.expires_at.tzinfo):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key has expired"
        )
    
    return api_key


async def get_optional_api_key(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
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