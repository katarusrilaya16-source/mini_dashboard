import sqlite3
import hashlib
import os
from datetime import datetime
from typing import Optional, List

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "users.db")


def hash_password(password: str) -> str:
    salted = f"streamlit_app_salt_{password}"
    return hashlib.sha256(salted.encode("utf-8")).hexdigest()


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_table():
    """Create the users table if it doesn't exist (safety net)."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT    NOT NULL,
            email      TEXT    NOT NULL UNIQUE,
            password   TEXT    NOT NULL,
            created_at TEXT    NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def add_user(name: str, email: str, password: str) -> tuple:
    """
    Insert a new user.
    Returns (True, "") on success or (False, error_message) on failure.
    """
    _ensure_table()
    hashed = hash_password(password)
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        conn = _get_connection()
        conn.execute(
            "INSERT INTO users (name, email, password, created_at) VALUES (?, ?, ?, ?)",
            (name.strip(), email.strip().lower(), hashed, created_at),
        )
        conn.commit()
        conn.close()
        return True, ""
    except sqlite3.IntegrityError:
        return False, "duplicate"
    except sqlite3.Error as e:
        return False, str(e)


def get_user(email: str) -> Optional[sqlite3.Row]:
    _ensure_table()
    try:
        conn = _get_connection()
        cursor = conn.execute(
            "SELECT id, name, email, password, created_at FROM users WHERE email = ?",
            (email.strip().lower(),),
        )
        row = cursor.fetchone()
        conn.close()
        return row
    except sqlite3.Error:
        return None


def get_all_users() -> List[sqlite3.Row]:
    _ensure_table()
    try:
        conn = _get_connection()
        cursor = conn.execute(
            "SELECT id, name, email, password, created_at FROM users ORDER BY created_at DESC"
        )
        rows = cursor.fetchall()
        conn.close()
        return rows
    except sqlite3.Error:
        return []


def user_exists(email: str) -> bool:
    return get_user(email) is not None


def verify_password(plain_password: str, stored_hash: str) -> bool:
    return hash_password(plain_password) == stored_hash