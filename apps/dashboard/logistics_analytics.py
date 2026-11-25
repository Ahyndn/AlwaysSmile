"""Analytics and duration conversions for the logistics dashboard."""

import math
import re
from collections import defaultdict
from statistics import median

SHIPPING_CONVERSIONS = {
    "ships overnight": 1.0,
    "ships in 1-2 business days": 2.1,
}

WARRANTY_CONVERSIONS = {
    "no warranty": 0.0,
    "1 week warranty": 7.0,
    "1 month warranty": 30.0,
    "1 year warranty": 365.0,
}

DURATION_PATTERN = re.compile(
    r"(?<![\w.-])(\d+(?:\.\d+)?)\s*"
    r"(business\s+days?|days?|weeks?|months?|years?)"
    r"(?!\w)",
    re.IGNORECASE,
)


def normalize_text(value):
    """Normalize text for consistent comparisons."""

    if value is None:
        return ""

    return " ".join(str(value).strip().lower().split())


def safe_number(value):
    """Return a finite, non-negative float or None."""

    if isinstance(value, bool) or value is None:
        return None

    try:
        number = float(value)

        if not math.isfinite(number) or number < 0:
            return None

        return number

    except (TypeError, ValueError, OverflowError):
        return None


def _parse_duration(value, conversion_type):
    """Convert a supported duration into days."""

    if not isinstance(value, str):
        return None

    match = DURATION_PATTERN.search(value)

    if not match:
        return None

    amount = safe_number(match.group(1))

    if amount is None:
        return None

    unit = match.group(2).lower()

    if conversion_type == "shipping":
        if "business" in unit:
            result = amount * 1.4
        elif "week" in unit:
            result = amount * 7
        elif "month" in unit:
            result = amount * 30
        elif "day" in unit:
            result = amount
        else:
            return None

    elif conversion_type == "warranty":
        if "week" in unit:
            result = amount * 7
        elif "month" in unit:
            result = amount * 30
        elif "year" in unit:
            result = amount * 365
        elif "day" in unit:
            result = amount
        else:
            return None

    else:
        return None

    if not math.isfinite(result):
        return None

    return round(result, 2) if conversion_type == "shipping" else result


def parse_shipping_days(value):
    """
    Convert shipping information into approximate calendar days.

    Business-day estimates use 1.4 calendar days per business day.
    The specified 1-2 business-day estimate uses 2.1 days.
    """

    text = normalize_text(value)

    if not text:
        return None

    if text in SHIPPING_CONVERSIONS:
        return SHIPPING_CONVERSIONS[text]

    return _parse_duration(text, "shipping")


def parse_warranty_days(value):
    """
    Convert numeric warranty durations into days.

    Lifetime warranties are excluded from numeric calculations.
    """

    text = normalize_text(value)

    if not text:
        return None

    if "lifetime" in text or "lifelong" in text:
        return None

    if text in WARRANTY_CONVERSIONS:
        return WARRANTY_CONVERSIONS[text]

    if "no warranty" in text:
        return 0.0

    return _parse_duration(text, "warranty")


def is_lifetime_warranty(value):
    """Identify lifetime or lifelong warranty descriptions."""

    text = normalize_text(value)

    return "lifetime" in text or "lifelong" in text


def calculate_logistics_analytics(products):
    """
    Calculate category-level logistics statistics.

    Each valid product is counted once.

    Missing and invalid measurements are excluded from their
    respective medians.

    Lifetime warranty products are counted and analysed separately.
    """

    if not isinstance(products, (list, tuple)):
        return []

    categories = defaultdict(
        lambda: {
            "product_count": 0,
            "prices": [],
            "ratings": [],
            "shipping_days": [],
            "warranty_days": [],
            "lifetime_count": 0,
            "lifetime_ratings": [],
            "lifetime_prices": [],
        }
    )

    for product in products:
        if not isinstance(product, dict):
            continue

        category = normalize_text(product.get("category"))

        if not category:
            category = "Uncategorized"
        else:
            category = str(product.get("category")).strip()

        record = categories[category]

        record["product_count"] += 1

        price = safe_number(product.get("price"))
        rating = safe_number(product.get("rating"))

        shipping = parse_shipping_days(product.get("shippingInformation"))

        warranty_information = product.get("warrantyInformation")

        warranty = parse_warranty_days(warranty_information)

        if price is not None:
            record["prices"].append(price)

        if rating is not None:
            record["ratings"].append(rating)

        if shipping is not None:
            record["shipping_days"].append(shipping)

        if warranty is not None:
            record["warranty_days"].append(warranty)

        if is_lifetime_warranty(warranty_information):
            record["lifetime_count"] += 1

            if rating is not None:
                record["lifetime_ratings"].append(rating)

            if price is not None:
                record["lifetime_prices"].append(price)

    results = []

    for category, record in sorted(categories.items()):
        prices = record["prices"]
        ratings = record["ratings"]
        shipping = record["shipping_days"]
        warranties = record["warranty_days"]

        lifetime_ratings = record["lifetime_ratings"]
        lifetime_prices = record["lifetime_prices"]

        results.append(
            {
                "category": category,
                "product_count": record["product_count"],
                "median_price": median(prices) if prices else None,
                "median_rating": median(ratings) if ratings else None,
                "median_shipping_days": (median(shipping) if shipping else None),
                "median_warranty_days": (median(warranties) if warranties else None),
                "lifetime_count": record["lifetime_count"],
                "lifetime_median_rating": (
                    median(lifetime_ratings) if lifetime_ratings else None
                ),
                "lifetime_median_price": (
                    median(lifetime_prices) if lifetime_prices else None
                ),
            }
        )

    return results

