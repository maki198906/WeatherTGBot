import sqlite3
from pathlib import Path

# Reuse the same database file as favourites
DB_PATH = Path(__file__).parent / "favourites.db"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_subscriptions_table() -> None:
    """Create the subscriptions table if it doesn't already exist."""
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                user_id   INTEGER PRIMARY KEY,
                city      TEXT    NOT NULL,
                send_time TEXT    NOT NULL,
                tz        TEXT    NOT NULL
            )
        """)


def save_subscription(user_id: int, city: str, send_time: str, tz: str) -> None:
    """Insert or update a subscription for the user (one per user)."""
    with _connect() as conn:
        conn.execute("""
            INSERT INTO subscriptions (user_id, city, send_time, tz)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                city      = excluded.city,
                send_time = excluded.send_time,
                tz        = excluded.tz
        """, (user_id, city, send_time, tz))


def get_subscription(user_id: int) -> dict | None:
    """Return the user's subscription, or None if not subscribed."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM subscriptions WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    return dict(row) if row else None


def remove_subscription(user_id: int) -> bool:
    """Remove a subscription. Returns True if it existed."""
    with _connect() as conn:
        cursor = conn.execute(
            "DELETE FROM subscriptions WHERE user_id = ?",
            (user_id,),
        )
    return cursor.rowcount > 0


def get_all_subscriptions() -> list[dict]:
    """Return all subscriptions — used at bot startup to restore scheduled jobs."""
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM subscriptions").fetchall()
    return [dict(row) for row in rows]
