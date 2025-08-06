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
            result = await session.execute(
                text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='model_strategies'"
                )
            )
            strategies_exists = result.fetchone() is not None
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
            result = await session.execute(
                text(
                    "SELECT table_name FROM information_schema.tables WHERE table_name = 'model_strategies'"
                )
            )
            strategies_exists = result.fetchone() is not None

        return providers_exists and api_keys_exists and strategies_exists
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
            result = await session.execute(text("PRAGMA table_info(model_strategies)"))
            strategy_columns = {row[1] for row in result.fetchall()}
            result = await session.execute(
                text("PRAGMA table_info(strategy_provider_mappings)")
            )
            mapping_columns = {row[1] for row in result.fetchall()}
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
            result = await session.execute(
                text(
                    """
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'model_strategies'
            """
                )
            )
            strategy_columns = {row[0] for row in result.fetchall()}
            result = await session.execute(
                text(
                    """
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'strategy_provider_mappings'
            """
                )
            )
            mapping_columns = {row[0] for row in result.fetchall()}

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
            "is_admin",
            "expires_at",
            "created_at",
            "updated_at",
        }

        required_strategy_columns = {
            "id",
            "name",
            "description",
            "strategy_type",
            "fallback_enabled",
            "fallback_order",
            "is_active",
            "created_at",
            "updated_at",
        }
        required_mapping_columns = {
            "id",
            "strategy_id",
            "provider_id",
            "large_models",
            "medium_models",
            "small_models",
            "selected_models",
            "priority",
            "is_active",
            "created_at",
            "updated_at",
        }

        providers_compatible = required_provider_columns.issubset(provider_columns)
        api_keys_compatible = required_api_key_columns.issubset(api_key_columns)
        strategies_compatible = required_strategy_columns.issubset(strategy_columns)
        mappings_compatible = required_mapping_columns.issubset(mapping_columns)

        return (
            providers_compatible
            and api_keys_compatible
            and strategies_compatible
            and mappings_compatible
        )
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

                result = await session.execute(
                    text("SELECT COUNT(*) FROM model_strategies")
                )
                info["strategies_count"] = result.scalar()
            except Exception:
                info["providers_count"] = "unknown"
                info["api_keys_count"] = "unknown"
                info["strategies_count"] = "unknown"

        return info
    except Exception as e:
        return {"error": str(e)}


async def init_db():
    """Initialize database with compatibility checking"""
    # Import models to ensure they're registered with SQLAlchemy
    from app.models.strategy import APIKey, ModelStrategy, Provider

    async with AsyncSessionLocal() as session:
        db_info = await get_database_info(session)

        if not db_info.get("tables_exist", False):
            # Database is empty, create all tables
            print("Database is empty. Creating tables...")
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            print("Database initialized successfully.")

            # Create default admin key
            await create_default_admin_key(session)
            # Create default strategies
            await create_default_strategies(session)
        else:
            # Database exists, check compatibility
            print(
                f"Database exists with {db_info.get('providers_count', 0)} providers, {db_info.get('api_keys_count', 0)} API keys, and {db_info.get('strategies_count', 0)} strategies."
            )
            print("Checking compatibility...")
            is_compatible = await check_database_compatibility(session)

            if is_compatible:
                print("Database is compatible. Using existing data.")
                # Check if admin key exists, create if not
                await create_default_admin_key(session)
                # Check if default strategies exist, create if not
                await create_default_strategies(session)
            else:
                print(
                    "Database schema is incompatible. Please backup data and recreate database."
                )
                raise RuntimeError(
                    "Incompatible database schema. Please backup your data and delete the database file to start fresh."
                )


async def create_default_admin_key(session: AsyncSession):
    """Create default admin key if none exists"""
    from sqlalchemy import select

    # Import all models to ensure they're registered with SQLAlchemy
    from app.models.strategy import APIKey, ModelStrategy, Provider
    from app.utils.api_key_generator import generate_openai_style_api_key

    # Check if any admin key exists
    result = await session.execute(select(APIKey))
    existing_keys = result.scalars().all()

    if not existing_keys:
        # Generate admin key
        admin_key = generate_openai_style_api_key()

        # Create admin key record
        db_key = APIKey(
            key_name="admin_default",
            api_key=admin_key,
            description="Default admin key for portal access",
            is_active=True,
            is_admin=True,  # Admin privileges
            expires_at=None,  # Never expires
        )

        session.add(db_key)
        await session.commit()

        print("=" * 60)
        print("🔑 DEFAULT ADMIN KEY CREATED")
        print("=" * 60)
        print(f"Admin Key: {admin_key}")
        print("This key is required to access the Vue.js portal at /portal (frontend)")
        print("Keep this key secure - it provides full administrative access!")
        print("=" * 60)
    else:
        print(f"Found {len(existing_keys)} existing API keys. No admin key created.")


async def create_default_strategies(session: AsyncSession):
    """Create default strategies if they don't exist"""
    from sqlalchemy import select

    # Import models to ensure they're registered with SQLAlchemy
    from app.models.strategy import ModelStrategy, Provider, StrategyProviderMapping

    # Check if providers exist first
    result = await session.execute(select(Provider))
    providers = result.scalars().all()

    if not providers:
        print("No providers found. Skipping default strategy creation.")
        return

    # Check if strategies exist
    result = await session.execute(select(ModelStrategy))
    existing_strategies = result.scalars().all()

    if len(existing_strategies) < 2:
        print("Creating default strategies...")

        # Check if Anthropic strategy exists
        anthropic_strategy = None
        openai_strategy = None

        for strategy in existing_strategies:
            if strategy.strategy_type == "anthropic":
                anthropic_strategy = strategy
            elif strategy.strategy_type == "openai":
                openai_strategy = strategy

        # Use the first provider for default strategies
        default_provider = providers[0]

        # Create Anthropic strategy if it doesn't exist
        if not anthropic_strategy:
            anthropic_strategy = ModelStrategy(
                name="Default Anthropic Strategy",
                description="Default strategy for Anthropic Claude models with 3-tier fallback",
                strategy_type="anthropic",
                fallback_enabled=True,
                fallback_order=["large", "medium", "small"],
                is_active=True,
            )
            session.add(anthropic_strategy)

        # Create OpenAI strategy if it doesn't exist
        if not openai_strategy:
            openai_strategy = ModelStrategy(
                name="Default OpenAI Strategy",
                description="Default strategy for OpenAI compatible models",
                strategy_type="openai",
                fallback_enabled=True,
                fallback_order=["large", "medium", "small"],
                is_active=True,
            )
            session.add(openai_strategy)

        # Flush to get IDs for the strategies
        await session.flush()

        # Create provider mapping for Anthropic strategy
        if not anthropic_strategy:
            anthropic_mapping = StrategyProviderMapping(
                strategy_id=anthropic_strategy.id,
                provider_id=default_provider.id,
                large_models=[
                    "claude-3-opus-20240229",
                    "claude-3-5-sonnet-20241022",
                ],
                medium_models=[
                    "claude-3-sonnet-20240229",
                    "claude-3-haiku-20240307",
                ],
                small_models=["claude-3-haiku-20240307"],
                priority=1,
                is_active=True,
            )
            session.add(anthropic_mapping)
            print("✓ Created default Anthropic strategy")

        # Create provider mapping for OpenAI strategy
        if not openai_strategy:
            openai_mapping = StrategyProviderMapping(
                strategy_id=openai_strategy.id,
                provider_id=default_provider.id,
                selected_models=[
                    "gpt-4",
                    "gpt-4-turbo",
                    "gpt-4o",
                    "gpt-3.5-turbo",
                    "gpt-3.5-turbo-16k",
                    "gpt-3.5-turbo-instruct",
                ],
                priority=1,
                is_active=True,
            )
            session.add(openai_mapping)
            print("✓ Created default OpenAI strategy")

        await session.commit()
        print("Default strategies created successfully.")
    else:
        print(
            f"Found {len(existing_strategies)} existing strategies. No default strategies created."
        )
