"""
Database migration: Remove UNIQUE constraint from users.name column.

This allows multiple users to have null names or the same name (e.g., "Unknown User")
since we now use clerk_user_id as the unique identifier.

Run with:
    python -m backend.migrations.remove_unique_constraint_from_name
"""

import logging
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.app.config import settings

logger = logging.getLogger(__name__)


def migrate():
    """Remove UNIQUE constraint from users.name column."""
    engine = create_engine(settings.database_url)

    logger.info("Starting migration: remove_unique_constraint_from_name")

    with engine.connect() as conn:
        try:
            # SQLite doesn't support DROP CONSTRAINT, so we need to recreate the table
            logger.info("Recreating users table without UNIQUE constraint on name...")

            # Step 1: Create new table with correct schema
            conn.execute(
                text(
                    """
                CREATE TABLE users_new (
                    id INTEGER PRIMARY KEY,
                    name VARCHAR,
                    email VARCHAR,
                    clerk_user_id VARCHAR,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL
                )
            """
                )
            )

            # Step 2: Copy data from old table
            conn.execute(
                text(
                    """
                INSERT INTO users_new (id, name, email, clerk_user_id, created_at, updated_at)
                SELECT id, name, email, clerk_user_id, created_at, updated_at
                FROM users
            """
                )
            )

            # Step 3: Drop old table
            conn.execute(text("DROP TABLE users"))

            # Step 4: Rename new table
            conn.execute(text("ALTER TABLE users_new RENAME TO users"))

            # Step 5: Recreate indexes
            conn.execute(
                text(
                    """
                CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email
                ON users(email) WHERE email IS NOT NULL
            """
                )
            )

            conn.execute(
                text(
                    """
                CREATE UNIQUE INDEX IF NOT EXISTS ix_users_clerk_user_id
                ON users(clerk_user_id) WHERE clerk_user_id IS NOT NULL
            """
                )
            )

            conn.commit()

            logger.info("Migration completed successfully")
            print("✅ Migration successful! Removed UNIQUE constraint from users.name")

        except Exception as e:
            conn.rollback()
            logger.error(f"Migration failed: {e}", exc_info=True)
            print(f"❌ Migration failed: {e}")
            raise


def rollback():
    """Rollback is complex - backup and restore database instead."""
    logger.warning("Rollback not supported for this migration")
    print("⚠️  Rollback not supported - restore from backup if needed")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Database migration to remove name UNIQUE constraint"
    )
    parser.add_argument(
        "--rollback", action="store_true", help="Rollback the migration (not supported)"
    )
    args = parser.parse_args()

    if args.rollback:
        rollback()
    else:
        migrate()
