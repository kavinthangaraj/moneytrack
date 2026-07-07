import sqlite3
import os
from contextlib import contextmanager

DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DB_PATH = os.path.join(DB_DIR, "expenses.db")


@contextmanager
def get_db():
    """Get a database connection with automatic cleanup."""
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    """Initialize database schema and default data."""
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('credit_card', 'savings', 'fastag', 'wallet', 'other')),
                last_four TEXT DEFAULT '',
                bank TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            );

            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                icon TEXT DEFAULT '📦',
                budget REAL DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            );

            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                amount REAL NOT NULL,
                description TEXT DEFAULT '',
                merchant TEXT DEFAULT '',
                category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
                account_id INTEGER REFERENCES accounts(id) ON DELETE SET NULL,
                type TEXT NOT NULL DEFAULT 'expense' CHECK(type IN ('expense', 'income', 'transfer')),
                date TEXT NOT NULL,
                sms_raw TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now', 'localtime')),
                updated_at TEXT DEFAULT (datetime('now', 'localtime'))
            );

            CREATE INDEX IF NOT EXISTS idx_tx_date ON transactions(date);
            CREATE INDEX IF NOT EXISTS idx_tx_category ON transactions(category_id);
            CREATE INDEX IF NOT EXISTS idx_tx_account ON transactions(account_id);
            CREATE INDEX IF NOT EXISTS idx_tx_type ON transactions(type);
        """)

        # Insert default categories if empty
        count = conn.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
        if count == 0:
            defaults = [
                ("Food & Dining", "🍔"),
                ("Transport", "🚗"),
                ("Shopping", "🛒"),
                ("Bills & Utilities", "💡"),
                ("Entertainment", "🎬"),
                ("Health", "💊"),
                ("Education", "📚"),
                ("Travel", "✈️"),
                ("Groceries", "🥬"),
                ("Personal Care", "🧴"),
                ("Subscriptions", "📱"),
                ("Rent", "🏠"),
                ("Savings & Investments", "💰"),
                ("FASTag / Tolls", "🛣️"),
                ("Other", "📦"),
            ]
            conn.executemany(
                "INSERT INTO categories (name, icon) VALUES (?, ?)", defaults
            )

        conn.commit()
