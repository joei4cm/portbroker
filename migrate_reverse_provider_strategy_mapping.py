#!/usr/bin/env python3
"""
Migration to reverse provider-strategy mapping
Instead of providers having a strategy_id, strategies will have provider mappings
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text

from app.core.database import AsyncSessionLocal


async def migrate_provider_strategy_mapping():
    """Reverse the provider-strategy mapping relationship"""

    async with AsyncSessionLocal() as db:
        # Check if the provider_priority column exists in model_strategies
        result = await db.execute(
            text(
                """
            PRAGMA table_info(model_strategies)
        """
            )
        )

        columns = [row[1] for row in result.fetchall()]
        has_provider_priority = "provider_priority" in columns

        if not has_provider_priority:
            print("Adding provider_priority column to model_strategies table...")
            await db.execute(
                text(
                    """
                ALTER TABLE model_strategies 
                ADD COLUMN provider_priority JSON DEFAULT '[]'
            """
                )
            )

        # Check if strategy_id column exists in providers table
        result = await db.execute(
            text(
                """
            PRAGMA table_info(providers)
        """
            )
        )

        columns = [row[1] for row in result.fetchall()]
        has_strategy_id = "strategy_id" in columns

        if has_strategy_id:
            print("Migrating existing provider-strategy relationships...")

            # Get all existing provider-strategy relationships
            result = await db.execute(
                text(
                    """
                SELECT p.id as provider_id, p.name as provider_name, 
                       s.id as strategy_id, s.name as strategy_name,
                       s.provider_priority as existing_priorities
                FROM providers p
                LEFT JOIN model_strategies s ON p.strategy_id = s.id
                WHERE p.strategy_id IS NOT NULL
            """
                )
            )

            relationships = result.fetchall()

            for rel in relationships:
                provider_id = rel.provider_id
                strategy_id = rel.strategy_id
                provider_name = rel.provider_name
                strategy_name = rel.strategy_name
                existing_priorities = rel.existing_priorities or []

                print(f"  Migrating: {provider_name} -> {strategy_name}")

                # Add provider to strategy's provider priority list if not already there
                if provider_id not in existing_priorities:
                    new_priorities = existing_priorities + [provider_id]
                    await db.execute(
                        text(
                            """
                        UPDATE model_strategies 
                        SET provider_priority = :priorities 
                        WHERE id = :strategy_id
                    """
                        ),
                        {"priorities": new_priorities, "strategy_id": strategy_id},
                    )

            # Remove the strategy_id column from providers table
            print("Removing strategy_id column from providers table...")
            # SQLite doesn't support DROP COLUMN directly, we need to recreate the table
            await db.execute(
                text(
                    """
                CREATE TABLE providers_new (
                    id INTEGER PRIMARY KEY,
                    name VARCHAR(100) NOT NULL UNIQUE,
                    provider_type VARCHAR(50) NOT NULL,
                    base_url VARCHAR(500) NOT NULL,
                    api_key VARCHAR(500) NOT NULL,
                    model_list JSON DEFAULT '[]' NOT NULL,
                    small_model VARCHAR(100),
                    medium_model VARCHAR(100),
                    big_model VARCHAR(100),
                    headers JSON,
                    is_active BOOLEAN DEFAULT 1 NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME
                )
            """
                )
            )

            await db.execute(
                text(
                    """
                INSERT INTO providers_new 
                SELECT id, name, provider_type, base_url, api_key, model_list, 
                       small_model, medium_model, big_model, headers, is_active, 
                       created_at, updated_at
                FROM providers
            """
                )
            )

            await db.execute(
                text(
                    """
                DROP TABLE providers
            """
                )
            )

            await db.execute(
                text(
                    """
                ALTER TABLE providers_new RENAME TO providers
            """
                )
            )

        await db.commit()
        print("Migration completed successfully!")


if __name__ == "__main__":
    asyncio.run(migrate_provider_strategy_mapping())
