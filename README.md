# Expense Tracker

Offline personal expense tracker. All data stays on your machine in a local SQLite database.

## Features

- **Manual entry** — log expenses, income, and transfers
- **SMS parser** — paste bank SMS messages, auto-extract amount/merchant/date/account
- **Category tracking** — 14 built-in categories, fully customizable
- **Account-wise tracking** — credit cards, debit cards, UPI, cash, wallets
- **Dashboard** — monthly totals, category breakdown, account breakdown, recent transactions
- **Search & filter** — by date range, category, account, type, or keyword
- **100% offline** — no network calls, no cloud, no telemetry

## Setup

```bash
cd expense-tracker
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open **http://localhost:8000** in your browser.

## Usage

### Quick Add
Click **+ Add** in the sidebar or go to Transactions → fill the form → Save.

### SMS Parser
Copy a bank SMS from your phone → paste it into the SMS Parser page → click **Parse** → review the extracted data → Save.

### Supported SMS Formats
- HDFC, ICICI, SBI, Axis, Kotak, and most Indian bank SMS
- UPI transaction messages (GPay, PhonePe, Paytm, etc.)
- Card transaction alerts
- Wallet transaction messages

## Data Location

All data is stored in `data/expenses.db` (SQLite). Back up this file to keep your data safe.

## Tech Stack

- **Backend**: Python, FastAPI, SQLite
- **Frontend**: React (CDN), Tailwind CSS
- **No build step** — `python app.py` is all you need
