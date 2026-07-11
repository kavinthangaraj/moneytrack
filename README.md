# MoneyTrack

Personal expense tracker with offline-first PWA support. Runs locally with SQLite or deploys to the cloud with PostgreSQL.

**Live:** https://moneytrack.fly.dev

## Features

- **Manual entry** — log expenses, income, and transfers
- **SMS parser** — paste Indian bank SMS messages, auto-extract amount, merchant, date, bank, and card/account details
- **Category tracking** — 15 built-in categories with emoji icons, fully customizable
- **Account-wise tracking** — credit cards, savings accounts, UPI, FASTag, wallets
- **Dashboard** — monthly expense/income totals, category breakdown with charts, account breakdown, recent transactions
- **Search & filter** — by date range, category, account, type, or keyword
- **Offline-first PWA** — works without network; IndexedDB caches data locally with a sync queue for writes made offline
- **Mobile-optimized** — bottom-sheet modals, safe-area padding, 16px inputs (no iOS zoom), installable as a home screen app

## SMS Parser

Supports transaction SMS from:
- **Banks:** HDFC, ICICI, SBI, Axis, Kotak, Bank of Baroda, PNB, Canara, Yes Bank, Federal Bank, IndusInd, and more
- **UPI apps:** Google Pay, PhonePe, Paytm, Amazon Pay, CRED, BHIM, WhatsApp Pay
- **Auto-detects:** amount, merchant name, transaction date, bank, card/account last 4 digits, UPI app, and guesses expense category from merchant

## Setup

### Local (SQLite)

```bash
cd moneytrack
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open **http://localhost:8000**.

### Fly.io (PostgreSQL)

```bash
# Set your Supabase/database URL
fly secrets set DATABASE_URL="postgresql://..."

# Deploy
~/.fly/bin/fly deploy --ha=false
```

The app auto-detects PostgreSQL from the `DATABASE_URL` environment variable. Without it, falls back to local SQLite in `data/expenses.db`.

## Usage

### Quick Add
Click **+ Add** in the sidebar or go to Transactions → fill the form → Save.

### SMS Parser
Copy a bank SMS from your phone → paste it into the SMS Parser page → click **Parse** → review the extracted data → Save.

### PWA Install
Open the deployed URL on your phone → tap "Add to Home Screen" for a native app-like experience.

## Tech Stack

- **Backend:** Python, FastAPI, Uvicorn/Gunicorn
- **Frontend:** React 18 (CDN), Tailwind CSS, Chart.js, Babel standalone
- **Database:** SQLite (local) / PostgreSQL via Supabase (production)
- **Offline layer:** IndexedDB with sync queue for write-ahead offline support
- **Deployment:** Fly.io (Singapore region), Dockerfile, auto-stop/start machines
- **No build step** — single `index.html`, `python app.py` is all you need locally

## Project Structure

```
moneytrack/
├── app.py              # FastAPI backend — CRUD + dashboard + SMS parse endpoints
├── database.py         # Dual-mode DB layer (SQLite / PostgreSQL with query translation)
├── sms_parser.py       # Indian bank SMS regex parser
├── test_sms_parser.py  # Parser tests
├── requirements.txt    # Python deps
├── fly.toml            # Fly.io config
├── Dockerfile          # Container build
└── static/
    ├── index.html      # Full React frontend (single file)
    ├── sw.js           # Service worker
    ├── manifest.json   # PWA manifest
    ├── icon-192.png
    └── icon-512.png
```
