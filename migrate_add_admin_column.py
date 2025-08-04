#!/usr/bin/env python3
"""
Database migration script to add is_admin column to api_keys table
"""
import asyncio
import sqlite3
from pathlib import Path


async def add_is_admin_column():
    """Add is_admin column to api_keys table"""
    db_path = Path("portbroker.db")

    if not db_path.exists():
        print("Database file not found")
        return

    # Connect to the database
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Check if column already exists
    cursor.execute("PRAGMA table_info(api_keys)")
    columns = [row[1] for row in cursor.fetchall()]

    if "is_admin" not in columns:
        print("Adding is_admin column to api_keys table...")

        # Add the column with a default value of False
        cursor.execute("ALTER TABLE api_keys ADD COLUMN is_admin BOOLEAN DEFAULT 0")

        # Update the admin key to have admin privileges
        cursor.execute(
            "UPDATE api_keys SET is_admin = 1 WHERE key_name = 'admin_default'"
        )

        # Commit the changes
        conn.commit()
        print("Migration completed successfully!")
    else:
        print("is_admin column already exists")

    # Close the connection
    conn.close()


if __name__ == "__main__":
    asyncio.run(add_is_admin_column())
