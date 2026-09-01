"""
Credit card statement parser for Indian banks (HDFC, ICICI, SBI, etc.).
Supports text-based PDFs (pymupdf) and scanned images (pytesseract OCR).
"""

import re
import os
from datetime import datetime

from sms_parser import MERCHANT_CATEGORIES


# ─── Date Parsing ─────────────────────────────────────────────


def parse_date(text):
    """Parse date from common Indian date formats."""
    if not text:
        return None

    text = text.strip().replace(".", "/").replace("-", "/")
    formats = [
        "%d/%m/%Y",
        "%d/%m/%y",
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

    return None


# ─── Amount Parsing ───────────────────────────────────────────


def parse_amount(text):
    """Parse amount from Indian currency formats like Rs.1,234.56 / INR 1234 / Rs. 649.00."""
    if not text:
        return None
    cleaned = text.replace(",", "").replace("₹", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


# ─── Category Guessing ────────────────────────────────────────


def guess_category(merchant_name):
    """Guess expense category from merchant name keywords."""
    if not merchant_name:
        return "Other"
    lower = merchant_name.lower()
    for keyword, category in MERCHANT_CATEGORIES.items():
        if keyword.lower() in lower:
            return category
    return "Other"


# ─── Text Extraction ─────────────────────────────────────────


def extract_text_pymupdf(file_path, password=None):
    """Extract text from a text-based PDF using pymupdf. Supports password-protected PDFs."""
    try:
        import pymupdf
        doc = pymupdf.open(file_path)
        if doc.is_encrypted:
            if not password:
                doc.close()
                return "__ENCRYPTED__"
            if not doc.authenticate(password):
                doc.close()
                return "__WRONG_PASSWORD__"
        text_parts = []
        for page in doc:
            text_parts.append(page.get_text())
        doc.close()
        return "\n".join(text_parts)
    except Exception as e:
        return ""


def extract_text_ocr(file_path, password=None):
    """Extract text from scanned PDF or image using pytesseract."""
    try:
        import pytesseract
        from PIL import Image
        import pymupdf

        # Check if it's a PDF — convert pages to images first
        if file_path.lower().endswith(".pdf"):
            doc = pymupdf.open(file_path)
            if doc.is_encrypted:
                if not password:
                    doc.close()
                    return "__ENCRYPTED__"
                if not doc.authenticate(password):
                    doc.close()
                    return "__WRONG_PASSWORD__"
            text_parts = []
            for page_num in range(len(doc)):
                page = doc[page_num]
                pix = page.get_pixmap(dpi=300)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                text = pytesseract.image_to_string(img, lang="eng")
                text_parts.append(text)
            doc.close()
            return "\n".join(text_parts)
        else:
            # Direct image file
            img = Image.open(file_path)
            return pytesseract.image_to_string(img, lang="eng")
    except Exception:
        return ""


def extract_text(file_path, password=None):
    """Extract text from PDF or image. Try pymupdf first, fall back to OCR."""
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        text = extract_text_pymupdf(file_path, password)
        if text in ("__ENCRYPTED__", "__WRONG_PASSWORD__"):
            return text
        # If very little text extracted, try OCR fallback
        if len(text.strip()) < 50:
            text = extract_text_ocr(file_path, password)
        return text
    elif ext in (".png", ".jpg", ".jpeg"):
        return extract_text_ocr(file_path)
    else:
        return ""


# ─── Transaction Line Parsing ─────────────────────────────────


def parse_statement_line(line):
    """
    Parse a single line from an Indian credit card statement.
    Typical formats:
        07/07/2026  SWIGGY BANGALORE  Rs.450.00
        01-07-2026  AMAZON.IN  INR 1,299.00
        15/06/2026  NETFLIX.COM  Rs. 649.00
    Returns {date, merchant, amount, raw_line} or None.
    """
    if not line or len(line.strip()) < 5:
        return None

    line = line.strip()

    # Skip common non-transaction lines
    skip_keywords = [
        "statement", "card number", "credit limit", "available limit",
        "payment due", "minimum amount", "total amount", "previous balance",
        "new transaction", "rewards", "gst", "interest", "late fee",
        "annual fee", "joining fee", "cardmember", "account summary",
        "page", "continued", "transaction details", "date",
        "please pay", "amount due", "billing", "cycle",
    ]
    lower_line = line.lower()
    for kw in skip_keywords:
        if kw in lower_line and "Rs" not in line and "INR" not in line:
            return None

    # Try to extract date, merchant, amount from the line
    date_str = None
    merchant = None
    amount = None

    # Pattern: date followed by description followed by amount
    # Date patterns: DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY, DD Mon YYYY
    date_pattern = r"(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{4})"

    # Amount patterns: Rs.X, Rs. X, INR X, Rs.X.XX, with optional commas
    amount_pattern = r"(?:Rs\.?|INR|₹)\s*([\d,]+\.?\d*)"

    # Try to find amount first
    amt_match = re.search(amount_pattern, line, re.IGNORECASE)
    if amt_match:
        amount = parse_amount(amt_match.group(1))

    # Try to find date
    date_match = re.search(date_pattern, line, re.IGNORECASE)
    if date_match:
        raw_date = date_match.group(1)
        date_str = parse_date(raw_date)

    # Extract merchant: text between date and amount
    if date_match:
        after_date = line[date_match.end():].strip()
    else:
        after_date = line

    if amt_match:
        merchant = after_date[:amt_match.start()].strip()
    else:
        merchant = after_date.strip()

    # Clean merchant name
    if merchant:
        # Remove leading/trailing delimiters, whitespace
        merchant = re.sub(r"^[\s\-–—|/\\:]+", "", merchant)
        merchant = re.sub(r"[\s\-–—|/\\:]+$", "", merchant)
        # Remove common suffixes like "*E", "*T", transaction type markers
        merchant = re.sub(r"\s*\*[A-Z]\s*$", "", merchant)
        # Truncate very long merchant names
        if len(merchant) > 80:
            merchant = merchant[:80].strip()

    # If we have date and amount, that's enough to be a valid transaction
    if date_str and amount and amount > 0:
        category = guess_category(merchant) if merchant else "Other"
        return {
            "date": date_str,
            "merchant": merchant or "",
            "amount": amount,
            "category": category,
            "raw_line": line,
        }

    return None


# ─── Main Parser ──────────────────────────────────────────────



def parse_markdown_table_line(line):
    """
    Parse a markdown table row like: | 18/08/2026 | SWIGGY | Rs.450.00 |
    Returns {date, merchant, amount, category, raw_line} or None.
    """
    if not line or '|' not in line:
        return None
    # Skip header/separator rows
    stripped = line.strip()
    if stripped.startswith('|--') or stripped.startswith('| --') or stripped.startswith('| :'):
        return None
    if '---' in stripped and 'date' not in stripped.lower():
        return None

    cells = [c.strip() for c in stripped.split('|')]
    # Remove empty leading/trailing cells from | ... | split
    cells = [c for c in cells if c]

    if len(cells) < 2:
        return None

    # Try to find date, merchant, amount from cells
    date_str = None
    merchant = None
    amount = None

    for i, cell in enumerate(cells):
        # Try as date
        if not date_str:
            d = parse_date(cell)
            if d:
                date_str = d
                continue
        # Try as amount
        amt_match = re.search(r'(?:Rs\.?|INR|₹)\s*([\d,]+\.?\d*)', cell, re.IGNORECASE)
        if amt_match:
            amount = parse_amount(amt_match.group(1))
            continue
        # Try plain number as amount (if > 10, likely a transaction amount)
        if not amount:
            plain = cell.replace(',', '').strip()
            try:
                val = float(plain)
                if val > 0:
                    amount = val
                    continue
            except ValueError:
                pass
        # Otherwise it's probably the merchant/description
        if not merchant and len(cell) > 1:
            merchant = cell

    if date_str and amount and amount > 0:
        category = guess_category(merchant) if merchant else "Other"
        return {
            "date": date_str,
            "merchant": merchant or "",
            "amount": amount,
            "category": category,
            "raw_line": stripped,
        }
    return None


def parse_statement(file_path, password=None):
    """
    Parse an Indian credit card statement (PDF, image, or markdown).
    Returns a list of dicts: [{date, merchant, amount, category, raw_line}]
    Raises ValueError if PDF is encrypted and no/wrong password provided.
    """
    import sys
    ext = os.path.splitext(file_path)[1].lower()

    # Markdown files — read directly, no PDF extraction needed
    if ext == ".md":
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
        if not text or len(text.strip()) < 5:
            return []
        transactions = []
        seen = set()
        for line in text.split("\n"):
            # Try markdown table row first
            result = parse_markdown_table_line(line)
            if not result:
                # Fall back to plain text line parsing
                result = parse_statement_line(line)
            if result:
                key = (result["date"], result["amount"], result["merchant"])
                if key not in seen:
                    seen.add(key)
                    transactions.append(result)
        return transactions

    if ext not in (".pdf", ".png", ".jpg", ".jpeg"):
        return []

    text = extract_text(file_path, password)
    print(f"[statement_parser] extract_text returned {len(text) if text else 0} chars, FULL TEXT:\n{text[:3000]}", file=sys.stderr)
    if text == "__ENCRYPTED__":
        raise ValueError("PDF is password-protected. Please provide the password.")
    if text == "__WRONG_PASSWORD__":
        raise ValueError("Incorrect PDF password. Please try again.")
    if not text or len(text.strip()) < 10:
        return []

    transactions = []
    seen = set()

    for i, line in enumerate(text.split("\n")):
        result = parse_statement_line(line)
        if result:
            # Deduplicate by date + amount + merchant
            key = (result["date"], result["amount"], result["merchant"])
            if key not in seen:
                seen.add(key)
                transactions.append(result)
        elif line.strip() and len(line.strip()) > 3:
            # Log lines that look like they might be transactions but weren't parsed
            stripped = line.strip()
            if any(c.isdigit() for c in stripped) and ("Rs" in stripped or "INR" in stripped or "₹" in stripped or len(stripped) > 15):
                print(f"[statement_parser] UNPARSED line {i}: {repr(stripped[:150])}", file=sys.stderr)

    print(f"[statement_parser] found {len(transactions)} transactions", file=sys.stderr)
    return transactions
