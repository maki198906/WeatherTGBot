import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "favourites.db"
MAX_CITIES = 3


def _connect() -> sqlite3.Connection:
    """Open a SQLite connection with row factory enabled."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create the favourites table if it doesn't already exist."""
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS favourites (
                user_id  INTEGER NOT NULL,
                city     TEXT    NOT NULL,
                saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, city COLLATE NOCASE)
            )
        """)


def get_cities(user_id: int) -> list[str]:
    """Return all saved cities for a user, ordered by save time."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT city FROM favourites WHERE user_id = ? ORDER BY saved_at",
            (user_id,),
        ).fetchall()
    return [row["city"] for row in rows]


def save_city(user_id: int, city: str) -> str:
    """
    Save a city for the user.
    Returns one of: 'saved' | 'duplicate' | 'limit_reached'
    """
    existing = get_cities(user_id)
    if any(c.lower() == city.lower() for c in existing):
        return "duplicate"
    if len(existing) >= MAX_CITIES:
        return "limit_reached"
    with _connect() as conn:
        conn.execute(
            "INSERT INTO favourites (user_id, city) VALUES (?, ?)",
            (user_id, city),
        )
    return "saved"


def remove_city(user_id: int, city: str) -> bool:
    """Remove a city for the user. Returns True if found and removed."""
    with _connect() as conn:
        cursor = conn.execute(
            "DELETE FROM favourites WHERE user_id = ? AND LOWER(city) = LOWER(?)",
            (user_id, city),
        )
    return cursor.rowcount > 0
