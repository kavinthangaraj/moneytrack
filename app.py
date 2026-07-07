"""
Expense Tracker — FastAPI backend.
Run: python app.py
Open: http://localhost:8000
"""

import os
from datetime import datetime, date
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from database import get_db, init_db
from sms_parser import parse_sms

# ─── App Setup ─────────────────────────────────────────────────

app = FastAPI(title="Expense Tracker")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")


@app.on_event("startup")
def startup():
    init_db()


# ─── Pydantic Models ───────────────────────────────────────────


class AccountCreate(BaseModel):
    name: str
    type: str  # credit_card, debit_card, upi, cash, wallet, other
    last_four: str = ""
    bank: str = ""


class AccountUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    last_four: Optional[str] = None
    bank: Optional[str] = None


class CategoryCreate(BaseModel):
    name: str
    icon: str = "📦"
    budget: float = 0


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    icon: Optional[str] = None
    budget: Optional[float] = None


class TransactionCreate(BaseModel):
    amount: float
    description: str = ""
    merchant: str = ""
    category_id: Optional[int] = None
    account_id: Optional[int] = None
    type: str = "expense"  # expense, income, transfer
    date: str = ""  # YYYY-MM-DD
    sms_raw: str = ""


class TransactionUpdate(BaseModel):
    amount: Optional[float] = None
    description: Optional[str] = None
    merchant: Optional[str] = None
    category_id: Optional[int] = None
    account_id: Optional[int] = None
    type: Optional[str] = None
    date: Optional[str] = None


class SmsParseRequest(BaseModel):
    text: str


# ─── Helper ────────────────────────────────────────────────────


def row_to_dict(row):
    """Convert sqlite3.Row to dict."""
    if row is None:
        return None
    return dict(row)


def rows_to_list(rows):
    return [dict(r) for r in rows]


# ─── Serve Frontend ────────────────────────────────────────────


@app.get("/")
def serve_index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/manifest.json")
def serve_manifest():
    return FileResponse(os.path.join(STATIC_DIR, "manifest.json"), media_type="application/json")


@app.get("/sw.js")
def serve_sw():
    return FileResponse(os.path.join(STATIC_DIR, "sw.js"), media_type="application/javascript")


@app.get("/icon-192.png")
def serve_icon_192():
    return FileResponse(os.path.join(STATIC_DIR, "icon-192.png"), media_type="image/png")


@app.get("/icon-512.png")
def serve_icon_512():
    return FileResponse(os.path.join(STATIC_DIR, "icon-512.png"), media_type="image/png")


# ─── Accounts CRUD ─────────────────────────────────────────────


@app.get("/api/accounts")
def list_accounts():
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM accounts ORDER BY name").fetchall()
        return rows_to_list(rows)


@app.post("/api/accounts")
def create_account(data: AccountCreate):
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO accounts (name, type, last_four, bank) VALUES (?, ?, ?, ?)",
            (data.name, data.type, data.last_four, data.bank),
        )
        conn.commit()
        account = conn.execute(
            "SELECT * FROM accounts WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
        return row_to_dict(account)


@app.put("/api/accounts/{account_id}")
def update_account(account_id: int, data: AccountUpdate):
    with get_db() as conn:
        existing = conn.execute(
            "SELECT * FROM accounts WHERE id = ?", (account_id,)
        ).fetchone()
        if not existing:
            raise HTTPException(404, "Account not found")

        updates = {}
        if data.name is not None:
            updates["name"] = data.name
        if data.type is not None:
            updates["type"] = data.type
        if data.last_four is not None:
            updates["last_four"] = data.last_four
        if data.bank is not None:
            updates["bank"] = data.bank

        if updates:
            set_clause = ", ".join(f"{k} = ?" for k in updates)
            values = list(updates.values()) + [account_id]
            conn.execute(f"UPDATE accounts SET {set_clause} WHERE id = ?", values)
            conn.commit()

        account = conn.execute(
            "SELECT * FROM accounts WHERE id = ?", (account_id,)
        ).fetchone()
        return row_to_dict(account)


@app.delete("/api/accounts/{account_id}")
def delete_account(account_id: int):
    with get_db() as conn:
        existing = conn.execute(
            "SELECT * FROM accounts WHERE id = ?", (account_id,)
        ).fetchone()
        if not existing:
            raise HTTPException(404, "Account not found")
        conn.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
        conn.commit()
        return {"ok": True}


# ─── Categories CRUD ───────────────────────────────────────────


@app.get("/api/categories")
def list_categories():
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM categories ORDER BY name").fetchall()
        return rows_to_list(rows)


@app.post("/api/categories")
def create_category(data: CategoryCreate):
    with get_db() as conn:
        try:
            cur = conn.execute(
                "INSERT INTO categories (name, icon, budget) VALUES (?, ?, ?)",
                (data.name, data.icon, data.budget),
            )
            conn.commit()
        except Exception:
            raise HTTPException(400, "Category name already exists")
        cat = conn.execute(
            "SELECT * FROM categories WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
        return row_to_dict(cat)


@app.put("/api/categories/{category_id}")
def update_category(category_id: int, data: CategoryUpdate):
    with get_db() as conn:
        existing = conn.execute(
            "SELECT * FROM categories WHERE id = ?", (category_id,)
        ).fetchone()
        if not existing:
            raise HTTPException(404, "Category not found")

        updates = {}
        if data.name is not None:
            updates["name"] = data.name
        if data.icon is not None:
            updates["icon"] = data.icon
        if data.budget is not None:
            updates["budget"] = data.budget

        if updates:
            set_clause = ", ".join(f"{k} = ?" for k in updates)
            values = list(updates.values()) + [category_id]
            conn.execute(f"UPDATE categories SET {set_clause} WHERE id = ?", values)
            conn.commit()

        cat = conn.execute(
            "SELECT * FROM categories WHERE id = ?", (category_id,)
        ).fetchone()
        return row_to_dict(cat)


@app.delete("/api/categories/{category_id}")
def delete_category(category_id: int):
    with get_db() as conn:
        existing = conn.execute(
            "SELECT * FROM categories WHERE id = ?", (category_id,)
        ).fetchone()
        if not existing:
            raise HTTPException(404, "Category not found")
        conn.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        conn.commit()
        return {"ok": True}


# ─── Transactions CRUD ─────────────────────────────────────────


@app.get("/api/transactions")
def list_transactions(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    category_id: Optional[int] = None,
    account_id: Optional[int] = None,
    tx_type: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
):
    with get_db() as conn:
        conditions = []
        params = []

        if start_date:
            conditions.append("t.date >= ?")
            params.append(start_date)
        if end_date:
            conditions.append("t.date <= ?")
            params.append(end_date)
        if category_id:
            conditions.append("t.category_id = ?")
            params.append(category_id)
        if account_id:
            conditions.append("t.account_id = ?")
            params.append(account_id)
        if tx_type:
            conditions.append("t.type = ?")
            params.append(tx_type)
        if search:
            conditions.append(
                "(t.description LIKE ? OR t.merchant LIKE ?)"
            )
            params.extend([f"%{search}%", f"%{search}%"])

        where = "WHERE " + " AND ".join(conditions) if conditions else ""

        # Get total count
        count_row = conn.execute(
            f"SELECT COUNT(*) as cnt FROM transactions t {where}", params
        ).fetchone()
        total = count_row["cnt"]

        # Get transactions with joined names
        rows = conn.execute(
            f"""
            SELECT t.*,
                   c.name as category_name, c.icon as category_icon,
                   a.name as account_name, a.type as account_type
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.id
            LEFT JOIN accounts a ON t.account_id = a.id
            {where}
            ORDER BY t.date DESC, t.created_at DESC
            LIMIT ? OFFSET ?
            """,
            params + [limit, offset],
        ).fetchall()

        return {"transactions": rows_to_list(rows), "total": total}


@app.post("/api/transactions")
def create_transaction(data: TransactionCreate):
    tx_date = data.date or date.today().isoformat()
    with get_db() as conn:
        cur = conn.execute(
            """INSERT INTO transactions
               (amount, description, merchant, category_id, account_id, type, date, sms_raw)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                data.amount,
                data.description,
                data.merchant,
                data.category_id,
                data.account_id,
                data.type,
                tx_date,
                data.sms_raw,
            ),
        )
        conn.commit()
        tx = conn.execute(
            """
            SELECT t.*,
                   c.name as category_name, c.icon as category_icon,
                   a.name as account_name, a.type as account_type
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.id
            LEFT JOIN accounts a ON t.account_id = a.id
            WHERE t.id = ?
            """,
            (cur.lastrowid,),
        ).fetchone()
        return row_to_dict(tx)


@app.put("/api/transactions/{tx_id}")
def update_transaction(tx_id: int, data: TransactionUpdate):
    with get_db() as conn:
        existing = conn.execute(
            "SELECT * FROM transactions WHERE id = ?", (tx_id,)
        ).fetchone()
        if not existing:
            raise HTTPException(404, "Transaction not found")

        updates = {"updated_at": datetime.now().isoformat()}
        if data.amount is not None:
            updates["amount"] = data.amount
        if data.description is not None:
            updates["description"] = data.description
        if data.merchant is not None:
            updates["merchant"] = data.merchant
        if data.category_id is not None:
            updates["category_id"] = data.category_id
        if data.account_id is not None:
            updates["account_id"] = data.account_id
        if data.type is not None:
            updates["type"] = data.type
        if data.date is not None:
            updates["date"] = data.date

        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [tx_id]
        conn.execute(f"UPDATE transactions SET {set_clause} WHERE id = ?", values)
        conn.commit()

        tx = conn.execute(
            """
            SELECT t.*,
                   c.name as category_name, c.icon as category_icon,
                   a.name as account_name, a.type as account_type
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.id
            LEFT JOIN accounts a ON t.account_id = a.id
            WHERE t.id = ?
            """,
            (tx_id,),
        ).fetchone()
        return row_to_dict(tx)


@app.delete("/api/transactions/{tx_id}")
def delete_transaction(tx_id: int):
    with get_db() as conn:
        existing = conn.execute(
            "SELECT * FROM transactions WHERE id = ?", (tx_id,)
        ).fetchone()
        if not existing:
            raise HTTPException(404, "Transaction not found")
        conn.execute("DELETE FROM transactions WHERE id = ?", (tx_id,))
        conn.commit()
        return {"ok": True}


# ─── SMS Parser ────────────────────────────────────────────────


@app.post("/api/sms/parse")
def parse_sms_endpoint(data: SmsParseRequest):
    result = parse_sms(data.text)
    if result is None:
        raise HTTPException(400, "Could not parse SMS")
    return result


# ─── Dashboard ─────────────────────────────────────────────────


@app.get("/api/dashboard")
def dashboard():
    now = datetime.now()
    month_start = now.strftime("%Y-%m-01")
    month_end = now.strftime("%Y-%m-31")

    with get_db() as conn:
        # This month total expenses
        row = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) as total FROM transactions WHERE type = 'expense' AND date >= ? AND date <= ?",
            (month_start, month_end),
        ).fetchone()
        this_month = row["total"]

        # This month income
        row = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) as total FROM transactions WHERE type = 'income' AND date >= ? AND date <= ?",
            (month_start, month_end),
        ).fetchone()
        this_month_income = row["total"]

        # Total transactions count
        row = conn.execute("SELECT COUNT(*) as cnt FROM transactions").fetchone()
        total_transactions = row["cnt"]

        # Average transaction (this month)
        row = conn.execute(
            "SELECT COALESCE(AVG(amount), 0) as avg_amt FROM transactions WHERE date >= ? AND date <= ?",
            (month_start, month_end),
        ).fetchone()
        avg_transaction = row["avg_amt"]

        # Category breakdown (this month)
        categories = conn.execute(
            """
            SELECT c.name, c.icon, COALESCE(SUM(t.amount), 0) as total, COUNT(t.id) as count
            FROM categories c
            LEFT JOIN transactions t ON t.category_id = c.id AND t.date >= ? AND t.date <= ? AND t.type = 'expense'
            GROUP BY c.id
            HAVING total > 0
            ORDER BY total DESC
            """,
            (month_start, month_end),
        ).fetchall()

        # Account breakdown (this month)
        accounts = conn.execute(
            """
            SELECT a.name, a.type, a.bank, COALESCE(SUM(t.amount), 0) as total, COUNT(t.id) as count
            FROM accounts a
            LEFT JOIN transactions t ON t.account_id = a.id AND t.date >= ? AND t.date <= ? AND t.type = 'expense'
            GROUP BY a.id
            HAVING total > 0
            ORDER BY total DESC
            """,
            (month_start, month_end),
        ).fetchall()

        # Top category
        top_cat = categories[0]["name"] if categories else None

        # Recent 10 transactions
        recent = conn.execute(
            """
            SELECT t.*,
                   c.name as category_name, c.icon as category_icon,
                   a.name as account_name, a.type as account_type
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.id
            LEFT JOIN accounts a ON t.account_id = a.id
            ORDER BY t.date DESC, t.created_at DESC
            LIMIT 10
            """
        ).fetchall()

        # Monthly trend (last 6 months)
        monthly = conn.execute(
            """
            SELECT strftime('%Y-%m', date) as month,
                   COALESCE(SUM(CASE WHEN type='expense' THEN amount ELSE 0 END), 0) as expenses,
                   COALESCE(SUM(CASE WHEN type='income' THEN amount ELSE 0 END), 0) as income
            FROM transactions
            WHERE date >= date('now', '-6 months')
            GROUP BY strftime('%Y-%m', date)
            ORDER BY month
            """
        ).fetchall()

        return {
            "this_month": this_month,
            "this_month_income": this_month_income,
            "total_transactions": total_transactions,
            "avg_transaction": round(avg_transaction, 2),
            "top_category": top_cat,
            "categories": rows_to_list(categories),
            "accounts": rows_to_list(accounts),
            "recent": rows_to_list(recent),
            "monthly": rows_to_list(monthly),
        }


# ─── Run ───────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    print("\n  💰 Expense Tracker")
    print("  ─────────────────")
    print("  Running on http://localhost:8000")
    print("  Press Ctrl+C to stop\n")

    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
