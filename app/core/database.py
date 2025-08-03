from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    pass


def get_database_url() -> str:
    if settings.database_type == "sqlite":
        return settings.database_url.replace("sqlite://", "sqlite+aiosqlite://")
    elif settings.database_type == "postgresql":
        if settings.database_url.startswith("postgresql://"):
            return settings.database_url.replace(
                "postgresql://", "postgresql+asyncpg://", 1
            )
        return settings.database_url
    elif settings.database_type == "supabase":
        if settings.supabase_url and settings.supabase_key:
            return f"postgresql+asyncpg://postgres:{settings.supabase_key}@{settings.supabase_url.replace('https://', '').replace('http://', '')}/postgres"
        raise ValueError("Supabase URL and key are required for Supabase database type")
    else:
        raise ValueError(f"Unsupported database type: {settings.database_type}")


database_url = get_database_url()
engine = create_async_engine(database_url, echo=settings.debug)
AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def check_database_exists(session: AsyncSession) -> bool:
    """Check if database tables exist"""
    try:
        # Check if providers table exists
        if settings.database_type == "sqlite":
            result = await session.execute(
                text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='providers'"
                )
            )
            providers_exists = result.fetchone() is not None
            result = await session.execute(
                text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='api_keys'"
                )
            )
            api_keys_exists = result.fetchone() is not None
        else:
            # PostgreSQL
            result = await session.execute(
                text(
                    "SELECT table_name FROM information_schema.tables WHERE table_name = 'providers'"
                )
            )
            providers_exists = result.fetchone() is not None
            result = await session.execute(
                text(
                    "SELECT table_name FROM information_schema.tables WHERE table_name = 'api_keys'"
                )
            )
            api_keys_exists = result.fetchone() is not None

        return providers_exists and api_keys_exists
    except Exception:
        return False


async def check_database_compatibility(session: AsyncSession) -> bool:
    """Check if existing database schema is compatible"""
    try:
        # Check providers table columns
        if settings.database_type == "sqlite":
            result = await session.execute(text("PRAGMA table_info(providers)"))
            provider_columns = {row[1] for row in result.fetchall()}
            result = await session.execute(text("PRAGMA table_info(api_keys)"))
            api_key_columns = {row[1] for row in result.fetchall()}
        else:
            # PostgreSQL
            result = await session.execute(
                text(
                    """
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'providers'
            """
                )
            )
            provider_columns = {row[0] for row in result.fetchall()}
            result = await session.execute(
                text(
                    """
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'api_keys'
            """
                )
            )
            api_key_columns = {row[0] for row in result.fetchall()}

        required_provider_columns = {
            "id",
            "name",
            "provider_type",
            "base_url",
            "api_key",
            "model_list",
            "big_model",
            "small_model",
            "medium_model",
            "is_active",
            "priority",
            "max_tokens",
            "temperature_default",
            "headers",
            "created_at",
            "updated_at",
        }

        required_api_key_columns = {
            "id",
            "key_name",
            "api_key",
            "description",
            "is_active",
            "expires_at",
            "created_at",
            "updated_at",
        }

        providers_compatible = required_provider_columns.issubset(provider_columns)
        api_keys_compatible = required_api_key_columns.issubset(api_key_columns)

        return providers_compatible and api_keys_compatible
    except Exception:
        return False


async def get_database_info(session: AsyncSession) -> dict:
    """Get database information for debugging"""
    try:
        info = {
            "database_type": settings.database_type,
            "tables_exist": await check_database_exists(session),
            "is_compatible": await check_database_compatibility(session),
        }

        # Count records if tables exist
        if info["tables_exist"]:
            try:
                result = await session.execute(text("SELECT COUNT(*) FROM providers"))
                info["providers_count"] = result.scalar()

                result = await session.execute(text("SELECT COUNT(*) FROM api_keys"))
                info["api_keys_count"] = result.scalar()
            except Exception:
                info["providers_count"] = "unknown"
                info["api_keys_count"] = "unknown"

        return info
    except Exception as e:
        return {"error": str(e)}


async def init_db():
    """Initialize database with compatibility checking"""
    async with AsyncSessionLocal() as session:
        db_info = await get_database_info(session)

        if not db_info.get("tables_exist", False):
            # Database is empty, create all tables
            print("Database is empty. Creating tables...")
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            print("Database initialized successfully.")
        else:
            # Database exists, check compatibility
            print(
                f"Database exists with {db_info.get('providers_count', 0)} providers and {db_info.get('api_keys_count', 0)} API keys."
            )
            print("Checking compatibility...")
            is_compatible = await check_database_compatibility(session)

            if is_compatible:
                print("Database is compatible. Using existing data.")
            else:
                print(
                    "Database schema is incompatible. Please backup data and recreate database."
                )
                raise RuntimeError(
                    "Incompatible database schema. Please backup your data and delete the database file to start fresh."
                )
