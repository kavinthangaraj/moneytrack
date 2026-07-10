"""
SMS parser for Indian bank transaction messages.
Handles formats from HDFC, ICICI, SBI, Axis, Kotak, and UPI apps.
"""

import re
from datetime import datetime


# ─── Bank Detection ───────────────────────────────────────────

BANK_KEYWORDS = {
    "hdfc": "HDFC Bank",
    "icici": "ICICI Bank",
    "sbi ": "SBI",
    "state bank": "SBI",
    "axis": "Axis Bank",
    "kotak": "Kotak Bank",
    "bank of baroda": "Bank of Baroda",
    "bob": "Bank of Baroda",
    "pnb": "Punjab National Bank",
    "punjab national": "Punjab National Bank",
    "canara": "Canara Bank",
    "yes bank": "Yes Bank",
    "idbi": "IDBI Bank",
    "federal bank": "Federal Bank",
    "indusind": "IndusInd Bank",
    "au bank": "AU Bank",
    "rbl bank": "RBL Bank",
    "slice": "Slice",
    "onecard": "OneCard",
    "amex": "American Express",
    "american express": "American Express",
}

UPI_APPS = {
    "google pay": "Google Pay",
    "gpay": "Google Pay",
    "phonepe": "PhonePe",
    "phone pe": "PhonePe",
    "paytm": "Paytm",
    "amazon pay": "Amazon Pay",
    "whatsapp": "WhatsApp Pay",
    "bhim": "BHIM UPI",
    "cred": "CRED",
    "freecharge": "Freecharge",
    "mobikwik": "MobiKwik",
    "payzapp": "PayZapp",
    "yono": "YONO SBI",
}

# ─── Category Guessing ────────────────────────────────────────

MERCHANT_CATEGORIES = {
    # Food & Dining
    "swiggy": "Food & Dining",
    "zomato": "Food & Dining",
    "dominos": "Food & Dining",
    "mcdonald": "Food & Dining",
    "kfc": "Food & Dining",
    "pizza hut": "Food & Dining",
    "subway": "Food & Dining",
    "starbucks": "Food & Dining",
    "cafe coffee": "Food & Dining",
    "CCD": "Food & Dining",
    "biryani": "Food & Dining",
    "restaurant": "Food & Dining",
    "food": "Food & Dining",
    "dine": "Food & Dining",
    "bakery": "Food & Dining",
    "sweet": "Food & Dining",
    "chaat": "Food & Dining",
    # Transport
    "uber": "Transport",
    "ola": "Transport",
    "rapido": "Transport",
    "metro": "Transport",
    "irctc": "Transport",
    "railway": "Transport",
    "irctc": "Transport",
    "fuel": "Transport",
    "petrol": "Transport",
    "diesel": "Transport",
    "parking": "Transport",
    "toll": "Transport",
    "auto": "Transport",
    # Shopping
    "amazon": "Shopping",
    "flipkart": "Shopping",
    "myntra": "Shopping",
    "meesho": "Shopping",
    "ajio": "Shopping",
    "nykaa": "Shopping",
    "tatacliq": "Shopping",
    "ajio": "Shopping",
    "lifestyle": "Shopping",
    "westside": "Shopping",
    "zara": "Shopping",
    "h&m": "Shopping",
    "ikea": "Shopping",
    # Bills & Utilities
    "electricity": "Bills & Utilities",
    "electric": "Bills & Utilities",
    "water bill": "Bills & Utilities",
    "gas bill": "Bills & Utilities",
    "broadband": "Bills & Utilities",
    "wifi": "Bills & Utilities",
    "jio": "Bills & Utilities",
    "airtel": "Bills & Utilities",
    "vi ": "Bills & Utilities",
    "bsnl": "Bills & Utilities",
    "recharge": "Bills & Utilities",
    "dth": "Bills & Utilities",
    # Entertainment
    "netflix": "Entertainment",
    "hotstar": "Entertainment",
    "disney": "Entertainment",
    "prime video": "Entertainment",
    "spotify": "Entertainment",
    "youtube": "Entertainment",
    "bookmyshow": "Entertainment",
    "pvr": "Entertainment",
    "inox": "Entertainment",
    "gaming": "Entertainment",
    # Health
    "pharmeasy": "Health",
    "1mg": "Health",
    "netmeds": "Health",
    "apollo": "Health",
    "medplus": "Health",
    "pharmacy": "Health",
    "hospital": "Health",
    "clinic": "Health",
    "doctor": "Health",
    "medical": "Health",
    # Groceries
    "bigbasket": "Groceries",
    "blinkit": "Groceries",
    "instamart": "Groceries",
    "zepto": "Groceries",
    "dmart": "Groceries",
    "reliance fresh": "Groceries",
    "more supermarket": "Groceries",
    "smart": "Groceries",
    "mart": "Groceries",
    "kirana": "Groceries",
    # Travel
    "makemytrip": "Travel",
    "goibibo": "Travel",
    "cleartrip": "Travel",
    "yatra": "Travel",
    "airbnb": "Travel",
    "booking.com": "Travel",
    "hotel": "Travel",
    "flight": "Travel",
    # Subscriptions
    "spotify": "Subscriptions",
    "youtube premium": "Subscriptions",
    "apple": "Subscriptions",
    "google storage": "Subscriptions",
    "icloud": "Subscriptions",
    "microsoft": "Subscriptions",
}


# ─── Parsing Functions ─────────────────────────────────────────


def parse_amount(text):
    """Extract numeric amount from text like '1,234.56'."""
    cleaned = text.replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_date(text):
    """Parse date from common Indian date formats."""
    if not text:
        return datetime.now().strftime("%Y-%m-%d")

    text = text.strip().replace(".", "/").replace("-", "/")
    formats = [
        "%d/%m/%Y",
        "%d/%m/%y",
        "%Y/%m/%d",
        "%d %b %Y",
        "%d %B %Y",
        "%b %d, %Y",
        "%B %d, %Y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue

    return datetime.now().strftime("%Y-%m-%d")


def detect_bank(sms_text):
    """Detect bank name from SMS content."""
    lower = sms_text.lower()
    for keyword, bank_name in BANK_KEYWORDS.items():
        if keyword in lower:
            return bank_name
    return None


def detect_upi_app(sms_text):
    """Detect UPI app from SMS content."""
    lower = sms_text.lower()
    for keyword, app_name in UPI_APPS.items():
        if keyword in lower:
            return app_name
    return None


def guess_category(merchant_name):
    """Guess expense category from merchant name keywords."""
    if not merchant_name:
        return None
    lower = merchant_name.lower()
    for keyword, category in MERCHANT_CATEGORIES.items():
        if keyword.lower() in lower:
            return category
    return "Other"


def detect_account_type(sms_text):
    """Detect payment method type from SMS."""
    lower = sms_text.lower()
    if any(x in lower for x in ["credit card", "credit ac", "cc ending", "credit limit"]):
        return "credit_card"
    if any(x in lower for x in ["debit card", "debit ac", "savings a/c", "sb a/c"]):
        return "debit_card"
    if any(x in lower for x in ["upi", "upi ref", "vpa", "upi transaction"]):
        return "upi"
    if any(x in lower for x in ["wallet", "paytm wallet", "amazon pay balance"]):
        return "wallet"
    return None


def extract_last_four(sms_text):
    """Extract last 4 digits of card or account number."""
    patterns = [
        r"ending\s+(\d{4})",
        r"card\s+(\d{4})",
        r"XX\s*(\d{4})",
        r"x\s*(\d{4})",
        r"A/c\s+\w*(\d{4})",
        r"no\.?\s*\*+(\d{4})",
    ]
    for p in patterns:
        match = re.search(p, sms_text, re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def extract_merchant(sms_text):
    """Extract merchant/payee name from SMS."""
    patterns = [
        # "at MERCHANT on DATE" or "to MERCHANT on DATE"
        r"(?:at|to|paid to|spent at|transferred to|payment to)\s+(.+?)(?=(?:\s+on\s+|\s+via\s+|\s+using\s+|\s+\.?\s*(?:Avl|UPI|Ref|Txn|available|Your|If)|\s*$))",
        # "merchant/store/shop: NAME"
        r"(?:merchant|store|shop|payee|beneficiary)[:\s]+(.+?)(?:\s*[.\n]|\s*$)",
        # "NAME has been paid"
        r"(.+?)\s+has been\s+(?:paid|credited|debited)",
    ]
    for p in patterns:
        match = re.search(p, sms_text, re.IGNORECASE)
        if match:
            merchant = match.group(1).strip().rstrip(".")
            # Clean up common suffixes
            merchant = re.sub(
                r"\s+(via|using|through|from|ref|txn).*$", "",
                merchant, flags=re.IGNORECASE,
            )
            # Skip if it's clearly not a merchant name
            if len(merchant) > 2 and len(merchant) < 80:
                return merchant
    return None


def parse_sms(sms_text):
    """
    Parse a bank transaction SMS and extract structured data.
    Returns a dict with amount, merchant, date, account info, and category guess.
    """
    if not sms_text or not sms_text.strip():
        return None

    result = {
        "amount": None,
        "merchant": None,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "account_type": None,
        "bank": None,
        "last_four": None,
        "upi_app": None,
        "category": None,
        "description": "",
        "raw_sms": sms_text.strip(),
        "confidence": "low",
    }

    # ── Amount ──
    amount_patterns = [
        r"(?:Rs\.?|INR|MRP)\s*([\d,]+\.?\d*)",
        r"([\d,]+\.?\d*)\s*(?:Rs\.?|INR)",
        r"(?:amount|amt)[:\s]+([\d,]+\.?\d*)",
    ]
    for p in amount_patterns:
        match = re.search(p, sms_text, re.IGNORECASE)
        if match:
            amt = parse_amount(match.group(1))
            if amt and amt > 0:
                result["amount"] = amt
                result["confidence"] = "medium"
                break

    # ── Date ──
    date_patterns = [
        r"on\s+(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4})",
        r"dated\s+(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4})",
        r"(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4})",
        r"on\s+(\d{1,2}\s+\w+\s+\d{4})",
    ]
    for p in date_patterns:
        match = re.search(p, sms_text, re.IGNORECASE)
        if match:
            parsed = parse_date(match.group(1))
            if parsed != datetime.now().strftime("%Y-%m-%d"):
                result["date"] = parsed
            break

    # ── Merchant ──
    result["merchant"] = extract_merchant(sms_text)

    # ── Bank ──
    result["bank"] = detect_bank(sms_text)

    # ── Account type ──
    result["account_type"] = detect_account_type(sms_text)

    # ── UPI app ──
    result["upi_app"] = detect_upi_app(sms_text)

    # ── Last four digits ──
    result["last_four"] = extract_last_four(sms_text)

    # ── Category guess ──
    if result["merchant"]:
        result["category"] = guess_category(result["merchant"])
        if result["category"] and result["category"] != "Other":
            result["confidence"] = "high"

    # ── Description ──
    # Use first sentence or first 120 chars as description
    first_line = sms_text.strip().split("\n")[0][:120]
    result["description"] = first_line

    return result
