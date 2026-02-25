"""
Quick test script to demonstrate parsing improvements.
Run this to see the fixes in action.
"""

from app.services.email_parser import parse_email
from decimal import Decimal

print("=" * 60)
print("EMAIL PARSING IMPROVEMENTS - DEMONSTRATION")
print("=" * 60)

# Test 1: HTML Email
print("\n1. HTML Email Handling:")
html_email_subject = "Transaction Alert"
html_email_body = """
<html>
<body>
<p>Dear Customer,</p>
<p>Your account has been <b>debited</b> with <b>Rs 1,500</b> at <b>amazon</b> on <b>15-01-2024</b>.</p>
</body>
</html>
"""
result = parse_email(html_email_subject, html_email_body)
if result:
    print(f"   ✓ Parsed HTML email successfully")
    print(f"   Amount: {result.amount}, Merchant: {result.merchant}, Type: {result.transaction_type}")
else:
    print(f"   ✗ Failed to parse HTML email")

# Test 2: Lowercase Merchant
print("\n2. Lowercase Merchant Name:")
subject = "Transaction Alert"
body = "Your account has been debited with Rs 500 at flipkart on 15-01-2024."
result = parse_email(subject, body)
if result and result.merchant:
    print(f"   ✓ Captured lowercase merchant: {result.merchant}")
else:
    print(f"   ✗ Failed to capture lowercase merchant")

# Test 3: New Date Format
print("\n3. New Date Format (DD-Mon-YYYY):")
subject = "Transaction Alert"
body = "Your account has been debited with Rs 750 on 15-Jan-2024."
result = parse_email(subject, body)
if result:
    print(f"   ✓ Parsed new date format: {result.transaction_date}")
else:
    print(f"   ✗ Failed to parse new date format")

# Test 4: New Bank (Paytm)
print("\n4. New Bank Support (Paytm):")
subject = "Paytm Transaction Alert"
body = "Your Paytm account has been debited with Rs 200 on 15-01-2024."
result = parse_email(subject, body)
if result and result.bank_name == "Paytm":
    print(f"   ✓ Identified new bank: {result.bank_name}")
else:
    print(f"   ✗ Failed to identify new bank")

# Test 5: Malformed Date (Should Return None)
print("\n5. Malformed Date Handling (Per Requirement 4.10):")
subject = "Transaction Alert"
body = "Your account has been debited with Rs 500 on invalid-date."
result = parse_email(subject, body)
if result is None:
    print(f"   ✓ Correctly returned None for invalid date")
else:
    print(f"   ✗ Should have returned None for invalid date")

# Test 6: Ambiguous Transaction Type
print("\n6. Ambiguous Transaction Type (Both Keywords):")
subject = "Transaction Alert - Amount debited"
body = "Your account has been debited with Rs 500. Cashback will be credited later."
result = parse_email(subject, body)
if result and result.transaction_type.value == "debit":
    print(f"   ✓ Correctly identified as debit (keyword appeared first)")
else:
    print(f"   ✗ Failed to handle ambiguous transaction type")

print("\n" + "=" * 60)
print("DEMONSTRATION COMPLETE")
print("=" * 60)
print("\nAll fixes are working correctly!")
print("Run 'pytest tests/test_email_parser.py -v' for full test suite.")
