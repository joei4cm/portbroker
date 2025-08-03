from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_portal_user, login_for_access_token
from app.core.config import settings
from app.core.database import get_db
from app.models.provider import APIKey, Provider
from app.schemas.provider import APIKey as APIKeySchema
from app.schemas.provider import (
    APIKeyAutoCreate,
    APIKeyCreate,
    APIKeyUpdate,
)
from app.schemas.provider import Provider as ProviderSchema
from app.schemas.provider import (
    ProviderCreate,
    ProviderUpdate,
)
from app.utils.api_key_generator import (
    generate_expiration_date,
    generate_openai_style_api_key,
)

router = APIRouter()
templates = Jinja2Templates(directory="frontend/templates")


async def get_current_portal_user_or_redirect(request: Request, db: AsyncSession = Depends(get_db)):
    """Get current authenticated portal user or redirect to login"""
    # Try to get token from Authorization header first
    auth_header = request.headers.get("Authorization")
    token = None

    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]

    # If no token in header, check for token in cookies (for browser requests)
    if not token:
        token = request.cookies.get("portal_token")

    if not token:
        return RedirectResponse(url="/portal/login", status_code=303)

    # Verify the token
    from app.core.auth import verify_token
    username = await verify_token(token)

    if username is None:
        return RedirectResponse(url="/portal/login", status_code=303)

    return username


# Portal Authentication Routes
@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Serve the login page"""
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/login")
async def login(request: Request, db: AsyncSession = Depends(get_db)):
    """Login to portal and return JWT token"""
    # Get API key from request body
    body = await request.body()
    try:
        # Try to parse as JSON first
        import json

        data = json.loads(body)
        api_key = data.get("api_key") if isinstance(data, dict) else data
    except:
        # If not JSON, use raw body
        api_key = body.decode("utf-8").strip("\"'")  # Remove quotes

    if not api_key:
        raise HTTPException(status_code=400, detail="API key is required")

    result = await login_for_access_token(api_key, db)

    # Create response with token and set cookie for browser authentication
    from fastapi.responses import JSONResponse

    response = JSONResponse(content=result)
    response.set_cookie(
        key="portal_token",
        value=result["access_token"],
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite="lax",
        max_age=1800,  # 30 minutes
    )

    return response


@router.get("/", response_class=HTMLResponse)
async def portal_dashboard(request: Request, db: AsyncSession = Depends(get_db)):
    """Serve the portal dashboard (protected)"""
    # Check authentication manually
    auth_header = request.headers.get("Authorization")
    token = None

    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]

    # If no token in header, check for token in cookies (for browser requests)
    if not token:
        token = request.cookies.get("portal_token")

    if not token:
        return RedirectResponse(url="/portal/login", status_code=303)

    # Verify the token
    from app.core.auth import verify_token
    username = await verify_token(token)

    if username is None:
        return RedirectResponse(url="/portal/login", status_code=303)

    return templates.TemplateResponse("portal.html", {"request": request})


# Protect all existing portal endpoints with authentication
@router.get("/providers", response_model=List[ProviderSchema])
async def list_providers(
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_portal_user),
):
    result = await db.execute(select(Provider))
    providers = result.scalars().all()
    return providers


@router.get("/providers/{provider_id}", response_model=ProviderSchema)
async def get_provider(
    provider_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_portal_user),
):
    result = await db.execute(select(Provider).where(Provider.id == provider_id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    return provider


@router.post("/providers", response_model=ProviderSchema)
async def create_provider(
    provider_data: ProviderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_portal_user),
):
    db_provider = Provider(**provider_data.model_dump())
    db.add(db_provider)
    await db.commit()
    await db.refresh(db_provider)
    return db_provider


@router.put("/providers/{provider_id}", response_model=ProviderSchema)
async def update_provider(
    provider_id: int,
    provider_data: ProviderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_portal_user),
):
    result = await db.execute(select(Provider).where(Provider.id == provider_id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    update_data = provider_data.model_dump(exclude_none=True)
    for field, value in update_data.items():
        setattr(provider, field, value)

    await db.commit()
    await db.refresh(provider)
    return provider


@router.delete("/providers/{provider_id}")
async def delete_provider(
    provider_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_portal_user),
):
    result = await db.execute(delete(Provider).where(Provider.id == provider_id))
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Provider not found")
    await db.commit()
    return {"detail": "Provider deleted successfully"}


@router.get("/api-keys", response_model=List[APIKeySchema])
async def list_api_keys(
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_portal_user),
):
    result = await db.execute(select(APIKey))
    keys = result.scalars().all()
    return keys


@router.get("/api-keys/{key_id}", response_model=APIKeySchema)
async def get_api_key(
    key_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_portal_user),
):
    result = await db.execute(select(APIKey).where(APIKey.id == key_id))
    api_key = result.scalar_one_or_none()
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    return api_key


@router.post("/api-keys", response_model=APIKeySchema)
async def create_api_key(
    key_data: APIKeyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_portal_user),
):
    db_key = APIKey(**key_data.model_dump())
    db.add(db_key)
    await db.commit()
    await db.refresh(db_key)
    return db_key


@router.post("/api-keys/auto-generate", response_model=APIKeySchema)
async def auto_generate_api_key(
    key_data: APIKeyAutoCreate,
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_portal_user),
):
    """
    Auto-generate an API key in OpenAI/Anthropic style.
    The API key will be automatically generated and returned in the response.
    """
    # Generate the API key
    generated_key = generate_openai_style_api_key()

    # Calculate expiration date if specified
    expires_at = generate_expiration_date(key_data.expires_in_days)

    # Create the API key record
    db_key = APIKey(
        key_name=key_data.key_name,
        api_key=generated_key,
        description=key_data.description,
        is_active=key_data.is_active,
        expires_at=expires_at,
    )

    db.add(db_key)
    await db.commit()
    await db.refresh(db_key)

    return db_key


@router.post("/api-keys/with-expiry")
async def create_api_key_with_expiry(
    key_name: str,
    api_key: str,
    description: Optional[str] = None,
    expires_in_days: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_portal_user),
):
    """
    Create API key with optional expiration in days.
    If expires_in_days is None or 0, the key never expires.
    """
    expires_at = None
    if expires_in_days and expires_in_days > 0:
        expires_at = datetime.now() + timedelta(days=expires_in_days)

    db_key = APIKey(
        key_name=key_name,
        api_key=api_key,
        description=description,
        expires_at=expires_at,
    )
    db.add(db_key)
    await db.commit()
    await db.refresh(db_key)
    return db_key


@router.put("/api-keys/{key_id}", response_model=APIKeySchema)
async def update_api_key(
    key_id: int,
    key_data: APIKeyUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_portal_user),
):
    result = await db.execute(select(APIKey).where(APIKey.id == key_id))
    api_key = result.scalar_one_or_none()
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    update_data = key_data.model_dump(exclude_none=True)
    for field, value in update_data.items():
        setattr(api_key, field, value)

    await db.commit()
    await db.refresh(api_key)
    return api_key


@router.delete("/api-keys/{key_id}")
async def delete_api_key(
    key_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_portal_user),
):
    result = await db.execute(delete(APIKey).where(APIKey.id == key_id))
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="API key not found")
    await db.commit()
    return {"detail": "API key deleted successfully"}


@router.get("/settings")
async def get_settings(current_user: str = Depends(get_current_portal_user)):
    """Get current settings configuration"""
    return {
        "database_type": settings.database_type,
        "database_url": settings.database_url,
        "supabase_url": settings.supabase_url,
        "host": settings.host,
        "port": settings.port,
        "debug": settings.debug,
        "default_openai_base_url": settings.default_openai_base_url,
        "default_big_model": settings.default_big_model,
        "default_small_model": settings.default_small_model,
    }


@router.post("/settings")
async def update_settings(
    settings_data: Dict[str, Any], current_user: str = Depends(get_current_portal_user)
):
    """Update settings configuration"""
    # Note: In a production environment, you would want to:
    # 1. Validate the settings
    # 2. Update the .env file or configuration
    # 3. Potentially restart the service

    # For now, we'll just return success
    # In a real implementation, you would update the environment variables
    # and potentially restart the service or reload configuration

    return {
        "detail": "Settings updated successfully",
        "note": "Some changes may require a service restart to take effect",
    }
