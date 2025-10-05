import sqlite3

conn = sqlite3.connect('/Users/pvasisht/dev/speakly/data/speakly.db')
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE todos ADD COLUMN ticktick_project_id TEXT;")
    conn.commit()
    print("✅ Column added successfully!")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("✅ Column already exists!")
    else:
        print(f"❌ Error: {e}")
finally:
    conn.close()
