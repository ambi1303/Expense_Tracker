"""
Intelligent category inference from merchant names and transaction context.

Uses rule-based matching with Indian merchants, UPI VPA patterns, and keywords
to auto-categorize transactions. Designed for zero external API dependency.
"""

import re
from typing import Optional
import structlog

logger = structlog.get_logger()

# Standard categories used across the app
CATEGORIES = [
    "Food",
    "Groceries",
    "Shopping",
    "Transport",
    "Bills",
    "Entertainment",
    "Healthcare",
    "Education",
    "Other",
]

# Merchant/keyword -> category mapping (lowercase for matching)
# Order matters: more specific patterns first
_MERCHANT_RULES: list[tuple[list[str], str]] = [
    # Food & Restaurants
    (["swiggy", "zomato", "dunzo", "uber eats", "dominos", "pizza hut", "mcdonald", "kfc",
      "cafe coffee day", "ccd", "starbucks", "chai point", "chaayos", "foodpanda", "eatsure"], "Food"),
    (["freshmenu", "faasos", "box8", "biryaniblues", "barbeque nation", "mainland china"], "Food"),

    # Groceries
    (["bigbasket", "big basket", "blinkit", "instamart", "zepto", "dunzo daily",
      "dmart", "d mart", "more supermarket", "reliance fresh", "nature's basket",
      "safal", "grofers", "jio mart", "jiomart"], "Groceries"),

    # Shopping
    (["amazon", "flipkart", "myntra", "ajio", "nykaa", "meesho", "snapdeal",
      "firstcry", "decathlon", "ikea", "homecentre", "urban ladder",
      "tatacliq", "limeroad", "bewakoof", "trendyol"], "Shopping"),
    (["paytm mall", "mall", "shopping"], "Shopping"),

    # Transport
    (["uber", "ola", "rapido", "meru", "bluesmart", "quick ride", "sride",
      "irctc", "irctc.co", "redbus", "abhibus", "make my trip", "makemytrip",
      "goibibo", "ixigo", "railway", "metro", "fuel", "petrol", "hp petrol",
      "iocl", "bharat petroleum", "indianoil", "shell"], "Transport"),

    # Bills & Utilities
    (["jio", "airtel", "bsnl", "vodafone", "vi ", "recharge", "electricity",
      "mseb", "tata power", "adani", "gas", "cylinder", "broadband",
      "act fibernet", "jiofiber", "airtel broadband", "spectra"], "Bills"),
    (["rent", "maintenance", "society", "property tax", "municipal"], "Bills"),

    # Entertainment
    (["netflix", "prime video", "amazon prime", "disney", "hotstar", "sonyliv",
      "zee5", "voot", "jiocinema", "youtube premium", "spotify", "gaana",
      "apple music", "bookmyshow", "inox", "pvr", "cinepolis", "gaming",
      "steam", "playstation", "xbox", "play store", "app store"], "Entertainment"),

    # Healthcare
    (["pharmacy", "medplus", "apollo", "netmeds", "1mg", "pharmeasy",
      "practo", "doctor", "hospital", "clinic", "labs", "pathology",
      "health", "medicine", "chemist"], "Healthcare"),

    # Education
    (["byju", "unacademy", "coursera", "udemy", "edx", "khan academy",
      "vedantu", "toppr", "whitehat", "school", "college", "tuition",
      "books", "stationery"], "Education"),

    # Subscriptions & Financial
    (["subscription", "subscriptions", "membership", "premium"], "Entertainment"),
]


def infer_category(
    merchant: Optional[str] = None,
    raw_snippet: Optional[str] = None,
    bank_name: Optional[str] = None,
) -> Optional[str]:
    """
    Infer transaction category from merchant name and context.

    Args:
        merchant: Merchant or payee name.
        raw_snippet: Raw transaction description/body.
        bank_name: Bank name (sometimes useful for context).

    Returns:
        Inferred category string, or None if no match.
    """
    text = " ".join(
        filter(None, [
            (merchant or "").lower(),
            (raw_snippet or "").lower(),
            (bank_name or "").lower(),
        ])
    )
    if not text.strip():
        return None

    # Remove common noise
    text = re.sub(r"[^\w\s]", " ", text)
    words = set(re.findall(r"\w+", text))

    for keywords, category in _MERCHANT_RULES:
        for kw in keywords:
            # Exact substring in original text (handles "swiggy" in "SWIGGY ORDER")
            if kw.replace(" ", "") in text.replace(" ", ""):
                return category
            # Word boundary match
            if re.search(rf"\b{re.escape(kw)}\b", text):
                return category
            # Multi-word: all parts present
            if " " in kw:
                parts = kw.split()
                if all(p in text for p in parts):
                    return category

    # UPI VPA heuristics (e.g. merchant@paytm -> often Shopping/Entertainment)
    if raw_snippet or merchant:
        combined = f"{(raw_snippet or '')} {(merchant or '')}".lower()
        if "@" in combined and any(x in combined for x in ["pay", "upi", "vpa"]):
            # Common UPI merchant patterns
            if any(x in combined for x in ["recharge", "jio", "airtel", "bill"]):
                return "Bills"
            if any(x in combined for x in ["food", "swiggy", "zomato", "restaurant"]):
                return "Food"
            if any(x in combined for x in ["petrol", "fuel", "transport"]):
                return "Transport"

    return None


def infer_and_log(merchant: Optional[str], raw_snippet: Optional[str]) -> Optional[str]:
    """
    Infer category and log for debugging. Use infer_category for production.
    """
    cat = infer_category(merchant=merchant, raw_snippet=raw_snippet)
    if cat:
        logger.debug(
            "category_inferred",
            merchant=merchant,
            category=cat,
        )
    return cat
