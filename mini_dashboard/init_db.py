import sqlite3
import hashlib
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "users.db")


def hash_password(password: str) -> str:
    salted = f"streamlit_app_salt_{password}"
    return hashlib.sha256(salted.encode("utf-8")).hexdigest()


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT    NOT NULL,
            email      TEXT    NOT NULL UNIQUE,
            password   TEXT    NOT NULL,
            created_at TEXT    NOT NULL
        )
    """)
    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        admin_hash = hash_password("Admin@123")
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            "INSERT INTO users (name, email, password, created_at) VALUES (?, ?, ?, ?)",
            ("Admin", "admin1@example.com", admin_hash, created_at),
        )
        conn.commit()
        print(f"[init_db] Default admin created: admin1@example.com / Admin@123")
    else:
        print(f"[init_db] DB already seeded, skipping.")

    conn.close()
    print(f"[init_db] Database ready at: {DB_PATH}")


if __name__ == "__main__":
    init_db()