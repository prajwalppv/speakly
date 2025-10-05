#!/bin/bash
# Production Cleanup Script for Speakly Backend
# Removes dead code, test artifacts, and temporary files

set -e

echo "🧹 Starting production cleanup..."

# Remove Python cache files
echo "Removing Python cache files..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true
find . -type f -name "*.pyd" -delete 2>/dev/null || true

# Remove test artifacts
echo "Removing test artifacts..."
rm -rf .pytest_cache
rm -rf htmlcov
rm -f .coverage
rm -f .coverage.*

# Remove dead code files (temporary test scripts)
echo "Removing temporary test scripts..."
rm -f add_column_migration.py
rm -f backfill_project_ids.py
rm -f cleanup.py
rm -f test_complete_only.py
rm -f test_fetch_task.py
rm -f test_task_updates.py
rm -f test_ticktick_crud.py

# Remove old migration scripts (keep alembic for proper migrations)
echo "Cleaning up old migration scripts..."
rm -rf scripts/

# Remove SQLite database (will use PostgreSQL in production)
echo "Removing local SQLite database..."
rm -f data/*.db
rm -f data/*.db-journal

# Remove local audio storage
echo "Cleaning audio storage..."
rm -rf storage/audio/*

# Remove log files
echo "Cleaning log files..."
rm -f logs/*.log
rm -f logs/*.json

# Create necessary empty directories for production
echo "Ensuring required directories exist..."
mkdir -p data
mkdir -p logs
mkdir -p storage/audio

# Create .gitkeep files to preserve directory structure
touch data/.gitkeep
touch logs/.gitkeep
touch storage/audio/.gitkeep

echo "✅ Cleanup complete!"
echo ""
echo "📦 Production-ready files:"
find . -type f -name "*.py" | grep -v __pycache__ | grep -v tests | wc -l | xargs echo "  - Python files:"
find tests -type f -name "*.py" 2>/dev/null | wc -l | xargs echo "  - Test files:"
echo ""
echo "Ready for deployment! 🚀"
