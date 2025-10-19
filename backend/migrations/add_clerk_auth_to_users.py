"""
Database migration: Add Clerk authentication fields to User model.

This migration adds:
- clerk_user_id: Unique identifier from Clerk
- email: User's email address
- Makes 'name' nullable (not all users have names)

Run with:
    python -m backend.migrations.add_clerk_auth_to_users
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
    """Apply the migration to add Clerk fields to users table."""
    engine = create_engine(settings.database_url)

    logger.info("Starting migration: add_clerk_auth_to_users")

    with engine.connect():
        try:
            # Check if columns already exist
            result = conn.execute(text("PRAGMA table_info(users)"))
            columns = {row[1] for row in result}

            migrations_applied = []

            # Add clerk_user_id column if it doesn't exist
            if "clerk_user_id" not in columns:
                conn.execute(
                    text(
                        """
                    ALTER TABLE users
                    ADD COLUMN clerk_user_id VARCHAR
                """
                    )
                )
                conn.execute(
                    text(
                        """
                    CREATE UNIQUE INDEX IF NOT EXISTS ix_users_clerk_user_id
                    ON users(clerk_user_id)
                """
                    )
                )
                migrations_applied.append("clerk_user_id")
                logger.info("Added clerk_user_id column with unique index")

            # Add email column if it doesn't exist
            if "email" not in columns:
                conn.execute(
                    text(
                        """
                    ALTER TABLE users
                    ADD COLUMN email VARCHAR
                """
                    )
                )
                conn.execute(
                    text(
                        """
                    CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email
                    ON users(email)
                """
                    )
                )
                migrations_applied.append("email")
                logger.info("Added email column with unique index")

            # Note: SQLite doesn't support ALTER COLUMN to make name nullable
            # We'll handle this in the application logic by allowing None values

            conn.commit()

            if migrations_applied:
                logger.info(
                    f"Migration completed successfully. Applied: {', '.join(migrations_applied)}"
                )
                print(
                    f"✅ Migration successful! Added columns: {', '.join(migrations_applied)}"
                )
            else:
                logger.info("Migration skipped - all columns already exist")
                print("✅ Migration skipped - database already up to date")

        except Exception as e:
            conn.rollback()
            logger.error(f"Migration failed: {e}", exc_info=True)
            print(f"❌ Migration failed: {e}")
            raise


def rollback():
    """Rollback the migration (remove Clerk fields)."""
    engine = create_engine(settings.database_url)

    logger.info("Rolling back migration: add_clerk_auth_to_users")

    with engine.connect() as conn:
        try:
            # SQLite doesn't support DROP COLUMN directly
            # We'd need to recreate the table, which is complex
            # For now, we'll just log a warning
            logger.warning(
                "SQLite doesn't support DROP COLUMN - manual rollback required"
            )
            print("⚠️  SQLite doesn't support DROP COLUMN.")
            print("To rollback, you need to:")
            print("1. Backup your data")
            print("2. Drop the users table")
            print("3. Recreate it without the Clerk fields")
            print("4. Restore your data")

        except Exception as e:
            logger.error(f"Rollback failed: {e}", exc_info=True)
            print(f"❌ Rollback failed: {e}")
            raise


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Database migration for Clerk auth")
    parser.add_argument(
        "--rollback",
        action="store_true",
        help="Rollback the migration instead of applying it",
    )
    args = parser.parse_args()

    if args.rollback:
        rollback()
    else:
        migrate()
