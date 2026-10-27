"""Helper: print the tables, schema and rows stored in the SQLite database."""
import sqlite3
import sys
from pathlib import Path

db_path = Path(__file__).parent / "instance" / "internships.db"
if not db_path.exists():
    sys.exit(f"Database file not found: {db_path}")

print("Database file:", db_path)
con = sqlite3.connect(db_path)
for name, sql in con.execute("SELECT name, sql FROM sqlite_master WHERE type='table'"):
    print("\nTABLE:", name)
    print(sql)
rows = con.execute("SELECT * FROM internship ORDER BY id").fetchall()
print(f"\nROWS in internship table: {len(rows)}")
for row in rows:
    print(row)
con.close()