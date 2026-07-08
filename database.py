import os
import re
import sqlite3
from contextlib import contextmanager

DATABASE_URL = os.environ.get("DATABASE_URL", "")
USE_POSTGRES = DATABASE_URL.startswith("postgres")


def get_psycopg2():
    """Import psycopg2 lazily."""
    import psycopg2
    import psycopg2.extras
    return psycopg2, psycopg2.extras


class PgConnection:
    """Wrapper to make psycopg2 behave like sqlite3.Row connections."""

    def __init__(self, conn):
        self._conn = conn
        self._lastrowid = None

    def execute(self, query, params=None):
        psycopg2, extras = get_psycopg2()
        pg_query = query.replace("?", "%s")
        pg_query = pg_query.replace("PRAGMA journal_mode=WAL", "-- noop")
        pg_query = pg_query.replace("PRAGMA foreign_keys=ON", "-- noop")
        pg_query = pg_query.replace("datetime('now', 'localtime')", "NOW()")
        pg_query = pg_query.replace("AUTOINCREMENT", "SERIAL")
        # Quote the 'date' column to avoid conflict with PostgreSQL's date() function
        pg_query = pg_query.replace("strftime('%Y-%m', date)", "TO_CHAR(\"date\"::date, 'YYYY-MM')")
        # Quote unquoted 'date' column references (but not table-qualified t.date which is already safe)
        pg_query = re.sub(r'(?<!\w|\.)date\s*>=\s*\?', '"date"::date >= %s', pg_query)
        pg_query = re.sub(r'(?<!\w|\.)date\s*<=\s*\?', '"date"::date <= %s', pg_query)
        pg_query = re.sub(r'(?<!\w|\.)date\s+DESC', '"date" DESC', pg_query)
        pg_query = re.sub(r'(?<!\w|\.)date\s+ASC', '"date" ASC', pg_query)
        # Also handle table-qualified t.date comparisons
        pg_query = re.sub(r'(\w\.)date\s*>=\s*\?', r'\1"date"::date >= %s', pg_query)
        pg_query = re.sub(r'(\w\.)date\s*<=\s*\?', r'\1"date"::date <= %s', pg_query)
        pg_query = re.sub(r'(\w\.)date\s+DESC', r'\1"date" DESC', pg_query)
        pg_query = re.sub(r'(\w\.)date\s+ASC', r'\1"date" ASC', pg_query)
        pg_query = pg_query.replace("date('now', '-6 months')", "(CURRENT_DATE - INTERVAL '6 months')")

        is_insert = pg_query.strip().upper().startswith("INSERT") and "RETURNING" not in pg_query.upper()
        if is_insert:
            pg_query = pg_query.rstrip(";").rstrip() + " RETURNING id"

        self._cur = self._conn.cursor(cursor_factory=extras.RealDictCursor)
        if params:
            self._cur.execute(pg_query, params)
        else:
            self._cur.execute(pg_query)

        if is_insert:
            row = self._cur.fetchone()
            self._lastrowid = row["id"] if row else None
        else:
            self._lastrowid = None
        return self

    def fetchone(self):
        return self._cur.fetchone() if self._cur else None

    def fetchall(self):
        return self._cur.fetchall() if self._cur else []

    def executescript(self, script):
        """Execute multiple statements (PostgreSQL)."""
        cur = self._conn.cursor()
        # Split by semicolons, filter empties
        stmts = [s.strip() for s in script.split(";") if s.strip()]
        for stmt in stmts:
            if not stmt.upper().startswith(("CREATE", "INSERT")):
                continue
            # Convert SQLite syntax to PostgreSQL
            pg = stmt.replace("datetime('now', 'localtime')", "NOW()")
            pg = pg.replace("AUTOINCREMENT", "SERIAL")
            pg = pg.replace("TEXT DEFAULT", "TEXT DEFAULT")
            # Remove CHECK constraints (not supported in SQLite migrations, not needed in PG)
            # Quote the 'date' column to avoid reserved keyword conflicts
            pg = re.sub(r'(?<!\w|\.)date(?=\s|$|,|\))', '"date"', pg, flags=re.IGNORECASE)
            pg = re.sub(r"\s*CHECK\([^)]+\)", "", pg, flags=re.IGNORECASE)
            try:
                cur.execute(pg)
            except Exception as e:
                # Only ignore "already exists" errors
                if "already exists" not in str(e).lower():
                    raise
        self._conn.commit()

    def commit(self):
        self._conn.commit()

    def close(self):
        self._conn.close()


class PgRow:
    """Make dict results accessible like sqlite3.Row."""
    def __init__(self, d):
        self._d = d

    def __getitem__(self, key):
        return self._d[key]

    def __contains__(self, key):
        return key in self._d

    def get(self, key, default=None):
        return self._d.get(key, default)

    def keys(self):
        return self._d.keys()


@contextmanager
def get_db():
    """Get a database connection — PostgreSQL or SQLite."""
    if USE_POSTGRES:
        psycopg2, extras = get_psycopg2()
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = False
        try:
            yield PgConnection(conn)
        finally:
            conn.close()
    else:
        db_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
        os.makedirs(db_dir, exist_ok=True)
        db_path = os.path.join(db_dir, "expenses.db")
        conn = sqlite3.connect(db_path)
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
        if USE_POSTGRES:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS accounts (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    last_four TEXT DEFAULT '',
                    bank TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT NOW()
                );

                CREATE TABLE IF NOT EXISTS categories (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    icon TEXT DEFAULT '📦',
                    budget REAL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT NOW()
                );

                CREATE TABLE IF NOT EXISTS transactions (
                    id SERIAL PRIMARY KEY,
                    amount REAL NOT NULL,
                    description TEXT DEFAULT '',
                    merchant TEXT DEFAULT '',
                    category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
                    account_id INTEGER REFERENCES accounts(id) ON DELETE SET NULL,
                    type TEXT NOT NULL DEFAULT 'expense',
                    "date" TEXT NOT NULL,
                    sms_raw TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                );

                CREATE INDEX IF NOT EXISTS idx_tx_date ON transactions("date");
                CREATE INDEX IF NOT EXISTS idx_tx_category ON transactions(category_id);
                CREATE INDEX IF NOT EXISTS idx_tx_account ON transactions(account_id);
                CREATE INDEX IF NOT EXISTS idx_tx_type ON transactions(type);
            """)
        else:
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
        count_row = conn.execute("SELECT COUNT(*) as cnt FROM categories").fetchone()
        count = count_row["cnt"] if isinstance(count_row, dict) else (count_row[0] if count_row else 0)
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
            for name, icon in defaults:
                conn.execute(
                    "INSERT INTO categories (name, icon) VALUES (?, ?)", (name, icon)
                )

        conn.commit()
