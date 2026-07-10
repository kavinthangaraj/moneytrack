"""Tests for sms_parser.py — merchant extraction and full parsing."""

from sms_parser import extract_merchant, parse_sms


# ─── extract_merchant() ───────────────────────────────────────

MERCHANT_CASES = [
    # (sms_text, expected_merchant)
    # Original 4 from the bug report
    ("Rs.450.00 debited from HDFC Bank Card ending 4521 at SWIGGY on 07/07/2026", "SWIGGY"),
    ("INR 1,299.00 spent on HDFC Bank Card XX5678 at AMAZON on 01/07/2026", "AMAZON"),
    ("Rs.150.00 paid to KIRANASTORE via Google Pay on 05/07/2026", "KIRANASTORE"),
    ("Your A/c XX1234 is debited for Rs.500.00 on 01/07/2026 at ZOMATO", "ZOMATO"),
    # Additional edge cases
    ("Rs.299.00 debited from SBI Card at NETFLIX on 10/06/2026", "NETFLIX"),
    ("INR 5,000.00 transferred to FLIPKART on 12/06/2026 via UPI", "FLIPKART"),
    ("Rs.89.00 paid to UBER via PhonePe on 03/07/2026", "UBER"),
    ("Your account XX9876 is debited for Rs.1,200.00 at DOMINOS", "DOMINOS"),
]


def test_extract_merchant():
    all_pass = True
    for sms, expected in MERCHANT_CASES:
        result = extract_merchant(sms)
        if result != expected:
            print(f"FAIL: got {result!r}, expected {expected!r}")
            print(f"  SMS: {sms}")
            all_pass = False
    if all_pass:
        print(f"PASS: all {len(MERCHANT_CASES)} merchant extraction cases")
    return all_pass


# ─── parse_sms() — full pipeline ─────────────────────────────

PARSE_CASES = [
    {
        "sms": "Rs.450.00 debited from HDFC Bank Card ending 4521 at SWIGGY on 07/07/2026",
        "expect": {"amount": 450.0, "merchant": "SWIGGY", "date": "2026-07-07", "bank": "HDFC Bank"},
    },
    {
        "sms": "Your A/c XX1234 is debited for Rs.500.00 on 01/07/2026 at ZOMATO",
        "expect": {"amount": 500.0, "merchant": "ZOMATO", "date": "2026-07-01"},
    },
    {
        "sms": "Rs.150.00 paid to KIRANASTORE via Google Pay on 05/07/2026",
        "expect": {"amount": 150.0, "merchant": "KIRANASTORE", "date": "2026-07-05", "upi_app": "Google Pay"},
    },
    {
        "sms": "INR 1,299.00 spent on HDFC Bank Card XX5678 at AMAZON on 01/07/2026",
        "expect": {"amount": 1299.0, "merchant": "AMAZON", "date": "2026-07-01", "bank": "HDFC Bank"},
    },
]


def test_parse_sms():
    all_pass = True
    for case in PARSE_CASES:
        result = parse_sms(case["sms"])
        for key, expected_val in case["expect"].items():
            actual_val = result.get(key)
            if actual_val != expected_val:
                print(f"FAIL: {key}={actual_val!r}, expected {expected_val!r}")
                print(f"  SMS: {case['sms']}")
                all_pass = False
    if all_pass:
        print(f"PASS: all {len(PARSE_CASES)} parse_sms cases")
    return all_pass


if __name__ == "__main__":
    ok = test_extract_merchant() and test_parse_sms()
    raise SystemExit(0 if ok else 1)
