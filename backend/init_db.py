#!/usr/bin/env python3
"""Initialize the SQLite database with all tables."""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import init_database
from app.models import User
from app.database import SessionLocal
from app.services import ensure_pj_profile

def main():
    print("🗄️  Initializing Speakly database...")
    
    # Create all tables
    init_database()
    print("✅ Database tables created")
    
    # Ensure default user exists
    with SessionLocal() as db:
        user = db.query(User).filter_by(name="default").one_or_none()
        if not user:
            user = User(name="default")
            db.add(user)
            db.commit()
            print("✅ Default user created")
        else:
            print("✅ Default user already exists")
    
    # Ensure PJ speaker profile exists
    with SessionLocal() as db:
        ensure_pj_profile(db)
        print("✅ PJ speaker profile ensured")
    
    print("\n🎉 Database initialization complete!")
    print(f"📍 Location: backend/data/app.db")

if __name__ == "__main__":
    main()
