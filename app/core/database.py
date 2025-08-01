from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings


class Base(DeclarativeBase):
    pass


def get_database_url() -> str:
    if settings.database_type == "sqlite":
        return settings.database_url.replace("sqlite://", "sqlite+aiosqlite://")
    elif settings.database_type == "postgresql":
        if settings.database_url.startswith("postgresql://"):
            return settings.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return settings.database_url
    elif settings.database_type == "supabase":
        if settings.supabase_url and settings.supabase_key:
            return f"postgresql+asyncpg://postgres:{settings.supabase_key}@{settings.supabase_url.replace('https://', '').replace('http://', '')}/postgres"
        raise ValueError("Supabase URL and key are required for Supabase database type")
    else:
        raise ValueError(f"Unsupported database type: {settings.database_type}")


database_url = get_database_url()
engine = create_async_engine(database_url, echo=settings.debug)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)