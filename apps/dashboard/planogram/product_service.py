"""
AlwaysSmile Department Store - Product Service

Responsibilities:
- Synchronize merchandise from DummyJSON.
- Normalize and validate product information.
- Cache products in the local Django database.
- Search the local merchandise catalogue.
- Retrieve individual products.
- Preserve existing planogram relationships.

DummyJSON is the external product catalogue.
The local MerchandiseProduct model is the operational cache.
"""

from decimal import Decimal, InvalidOperation

import requests
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q

from apps.dashboard.models import MerchandiseProduct

# ============================================================
# CONFIGURATION
# ============================================================

PRODUCT_API = "https://dummyjson.com/products"

REQUEST_TIMEOUT = 20

DEFAULT_PAGE_LIMIT = 100

MAX_PAGE_LIMIT = 100

MAX_PRODUCT_TITLE_LENGTH = 250
MAX_CATEGORY_LENGTH = 100
MAX_BRAND_LENGTH = 150


# ============================================================
# VALIDATION AND NORMALIZATION
# ============================================================


def decimal_value(value):
    """
    Convert a value into a non-negative Decimal.

    Invalid values become Decimal("0").
    """

    try:
        result = Decimal(str(value))

        if not result.is_finite() or result < 0:
            return Decimal("0")

        return result

    except (InvalidOperation, TypeError, ValueError, OverflowError):
        return Decimal("0")


def integer_value(value, default=0):
    """
    Safely convert a value into a non-negative integer.
    """

    if isinstance(value, bool):
        return default

    try:
        result = int(value)

        if result < 0:
            return default

        return result

    except (TypeError, ValueError, OverflowError):
        return default


def normalize_text(value, max_length, default=""):
    """
    Normalize external text fields.
    """

    if not isinstance(value, str):
        return default

    return value.strip()[:max_length]


def normalize_product(item):
    """
    Convert a DummyJSON product into local model fields.

    Invalid external product IDs are rejected.
    """

    if not isinstance(item, dict):
        raise ValidationError("Invalid product data.")

    external_id = integer_value(item.get("id"))

    if external_id < 1:
        raise ValidationError("Invalid external product ID.")

    dimensions = item.get("dimensions")

    if not isinstance(dimensions, dict):
        dimensions = {}

    thumbnail = normalize_text(
        item.get("thumbnail"),
        500,
    )

    return {
        "external_id": external_id,
        "title": normalize_text(
            item.get("title"),
            MAX_PRODUCT_TITLE_LENGTH,
            "Unknown Product",
        )
        or "Unknown Product",
        "category": normalize_text(
            item.get("category"),
            MAX_CATEGORY_LENGTH,
        ),
        "brand": normalize_text(
            item.get("brand"),
            MAX_BRAND_LENGTH,
        ),
        "price": decimal_value(item.get("price")),
        "weight": decimal_value(item.get("weight")),
        "width": decimal_value(dimensions.get("width")),
        "height": decimal_value(dimensions.get("height")),
        "depth": decimal_value(dimensions.get("depth")),
        "thumbnail": thumbnail,
        "stock": integer_value(item.get("stock")),
    }


# ============================================================
# FETCH EXTERNAL PRODUCTS
# ============================================================


def fetch_products():
    """
    Retrieve the complete DummyJSON product catalogue.

    Raises:
        requests.RequestException:
            If the external request fails.

        ValidationError:
            If the API response is invalid.
    """

    try:
        response = requests.get(
            PRODUCT_API,
            params={"limit": 0},
            timeout=REQUEST_TIMEOUT,
        )

        response.raise_for_status()

        payload = response.json()

    except requests.RequestException:
        raise

    except ValueError as exc:
        raise ValidationError("DummyJSON returned an invalid JSON response.") from exc

    if not isinstance(payload, dict):
        raise ValidationError("Invalid DummyJSON response.")

    products = payload.get("products")

    if not isinstance(products, list):
        raise ValidationError("DummyJSON product catalogue is missing.")

    return products


# ============================================================
# PRODUCT SYNCHRONIZATION
# ============================================================


@transaction.atomic
def synchronize_products():
    """
    Synchronize DummyJSON products into the local database.

    Existing products are updated.

    Products already assigned to planograms are preserved
    because this operation never deletes local products.

    Returns:
        QuerySet containing synchronized products.
    """

    external_products = fetch_products()

    synchronized_ids = set()

    for item in external_products:
        try:
            product_data = normalize_product(item)

        except ValidationError:
            continue

        external_id = product_data.pop("external_id")

        MerchandiseProduct.objects.update_or_create(
            external_id=external_id,
            defaults=product_data,
        )

        synchronized_ids.add(external_id)

    return MerchandiseProduct.objects.filter(external_id__in=synchronized_ids).order_by(
        "title"
    )


# ============================================================
# PRODUCT SEARCH
# ============================================================


def get_products(search=""):
    """
    Search the local merchandise catalogue.

    Searchable fields:
        - Product title
        - Category
        - Brand
        - External product ID
    """

    products = MerchandiseProduct.objects.all()

    if search is not None:
        if not isinstance(search, str):
            raise ValidationError("Product search must be text.")

        search = search.strip()

    if search:
        search_filter = (
            Q(title__icontains=search)
            | Q(category__icontains=search)
            | Q(brand__icontains=search)
        )

        if search.isdigit():
            search_filter |= Q(external_id=int(search))

        products = products.filter(search_filter)

    return products.order_by("title", "id")


# ============================================================
# PRODUCT RETRIEVAL
# ============================================================


def get_product(product_id):
    """
    Retrieve a local merchandise product by database ID.
    """

    if isinstance(product_id, bool):
        raise ValidationError("A valid product ID is required.")

    try:
        product_id = int(product_id)

        if product_id < 1:
            raise ValueError

    except (TypeError, ValueError, OverflowError):
        raise ValidationError("A valid product ID is required.")

    try:
        return MerchandiseProduct.objects.get(pk=product_id)

    except MerchandiseProduct.DoesNotExist:
        raise ValidationError("Merchandise product not found.")


def get_product_by_external_id(external_id):
    """
    Retrieve a product using its DummyJSON external ID.
    """

    if isinstance(external_id, bool):
        raise ValidationError("A valid external product ID is required.")

    try:
        external_id = int(external_id)

        if external_id < 1:
            raise ValueError

    except (TypeError, ValueError, OverflowError):
        raise ValidationError("A valid external product ID is required.")

    try:
        return MerchandiseProduct.objects.get(external_id=external_id)

    except MerchandiseProduct.DoesNotExist:
        raise ValidationError("Merchandise product not found.")


# ============================================================
# PRODUCT CATALOGUE STATISTICS
# ============================================================


def get_product_catalogue_summary():
    """
    Return basic merchandise catalogue statistics.
    """

    products = MerchandiseProduct.objects.all()

    return {
        "total_products": products.count(),
        "total_categories": (
            products.values("category").exclude(category="").distinct().count()
        ),
        "total_brands": (products.values("brand").exclude(brand="").distinct().count()),
        "total_stock": sum(products.values_list("stock", flat=True)),
    }

