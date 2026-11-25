from decimal import Decimal, InvalidOperation

SESSION_KEY = "low_stock_orders"


def _parse_integer(value, field_name):
    """Validate an integer without accepting fractional or Boolean values."""

    if isinstance(value, bool):
        raise ValueError(f"Invalid {field_name}.")

    try:
        parsed = int(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError(f"Invalid {field_name}.") from error

    if isinstance(value, (float, Decimal)):
        decimal_value = Decimal(str(value))

        if not decimal_value.is_finite():
            raise ValueError(f"Invalid {field_name}.")

        if decimal_value != Decimal(parsed):
            raise ValueError(f"Invalid {field_name}.")

    if isinstance(value, str) and str(parsed) != value.strip():
        raise ValueError(f"Invalid {field_name}.")

    return parsed


def _parse_price(value):
    """Validate a non-negative finite monetary value."""

    try:
        price = Decimal(str(value))
    except (TypeError, ValueError, InvalidOperation) as error:
        raise ValueError("Invalid product price.") from error

    if not price.is_finite() or price < 0:
        raise ValueError("Invalid product price.")

    return price


def _get_reorder_level(product):
    """
    Retrieve the stock threshold.

    Prefer the API's reorderLevel field.
    Fall back to minimumOrderQuantity for compatibility
    with the existing inventory analytics.
    """

    value = product.get("reorderLevel")

    if value is None:
        value = product.get("minimumOrderQuantity", 0)

    return _parse_integer(
        value or 0,
        "reorder level",
    )


def _validate_saved_order(order):
    """Validate one previously saved order."""

    if not isinstance(order, dict):
        raise ValueError("Invalid saved order.")

    try:
        product_id = order["product_id"]
        title = order["title"]
        price = _parse_price(order["price"])

        quantity = _parse_integer(
            order["quantity"],
            "saved order quantity",
        )

        if (
            product_id is None
            or str(product_id).strip() == ""
            or not isinstance(title, str)
            or quantity < 1
        ):
            raise ValueError

    except (
        KeyError,
        TypeError,
        ValueError,
        InvalidOperation,
        OverflowError,
    ) as error:
        raise ValueError("Invalid saved order.") from error

    return {
        "product_id": str(product_id),
        "title": title,
        "price": str(price),
        "quantity": quantity,
    }


def get_low_stock_orders(request):
    """Retrieve and validate saved low-stock orders."""

    orders = request.session.get(SESSION_KEY, {})

    if not isinstance(orders, dict):
        raise ValueError("Invalid saved orders.")

    validated = {}

    for product_id, order in orders.items():
        validated_order = _validate_saved_order(order)

        if str(product_id) != validated_order["product_id"]:
            raise ValueError("Invalid saved order.")

        validated[str(product_id)] = validated_order

    return validated


def save_low_stock_orders(request, orders):
    """Save validated orders to the current session."""

    if not isinstance(orders, dict):
        raise ValueError("Orders must be a dictionary.")

    validated = {}

    for product_id, order in orders.items():
        validated_order = _validate_saved_order(order)

        if str(product_id) != validated_order["product_id"]:
            raise ValueError("Invalid saved order.")

        validated[str(product_id)] = validated_order

    request.session[SESSION_KEY] = validated
    request.session.modified = True


def clear_low_stock_orders(request):
    """Remove all saved low-stock orders."""

    request.session.pop(SESSION_KEY, None)
    request.session.modified = True


def delete_low_stock_order(request, product_id):
    """Delete an individual saved order."""

    orders = get_low_stock_orders(request)

    orders.pop(str(product_id), None)

    save_low_stock_orders(request, orders)


def build_low_stock_orders(products):
    """
    Return products with available stock at or below
    their reorder threshold.

    Products with zero stock are excluded because they
    belong on the Out of Stock page.
    """

    results = []

    for product in products:
        if not isinstance(product, dict):
            continue

        try:
            stock = _parse_integer(
                product.get("stock", 0) or 0,
                "stock",
            )

            reorder_level = _get_reorder_level(product)

            minimum = _parse_integer(
                product.get("minimumOrderQuantity", 0) or 0,
                "minimum order quantity",
            )

            price = _parse_price(product.get("price", 0))

            if stock < 0 or reorder_level < 0 or minimum < 0:
                continue

        except ValueError:
            continue

        # Exclude out-of-stock products.
        if stock == 0:
            continue

        # Exclude products above their reorder threshold.
        if stock > reorder_level:
            continue

        product_id = product.get("id")

        if product_id is None or str(product_id).strip() == "":
            continue

        metadata = product.get("meta") or {}

        if not isinstance(metadata, dict):
            metadata = {}

        results.append(
            {
                "id": str(product_id),
                "title": product.get("title") or "Unknown",
                "category": product.get("category") or "Unknown",
                "sku": product.get("sku") or "N/A",
                "price": price,
                "stock": stock,
                "reorder_level": reorder_level,
                "minimum_order_quantity": minimum,
                "barcode": metadata.get("barcode", ""),
                "availability_status": (product.get("availabilityStatus") or "Unknown"),
                "quantity_to_order": max(
                    1,
                    minimum - stock,
                ),
            }
        )

    return results


def add_low_stock_order(request, product, quantity):
    """Add or accumulate a validated low-stock order."""

    if not isinstance(product, dict):
        raise ValueError("Invalid product.")

    quantity = _parse_integer(
        quantity,
        "order quantity",
    )

    if quantity < 1:
        raise ValueError("Quantity must be positive.")

    product_id = product.get("id")

    if product_id is None or str(product_id).strip() == "":
        raise ValueError("Invalid product ID.")

    product_id = str(product_id)

    try:
        stock = _parse_integer(
            product.get("stock", 0) or 0,
            "stock",
        )

        reorder_level = _get_reorder_level(product)

        price = _parse_price(product.get("price", 0))

    except ValueError as error:
        raise ValueError("Invalid product information.") from error

    if stock <= 0:
        raise ValueError("Product is no longer low stock.")

    if stock > reorder_level:
        raise ValueError("Product no longer meets the low-stock threshold.")

    # Validate existing orders before modifying the session.
    orders = get_low_stock_orders(request)

    existing = orders.get(product_id)

    existing_quantity = existing["quantity"] if existing else 0

    orders[product_id] = {
        "product_id": product_id,
        "title": str(product.get("title") or "Unknown"),
        "price": str(price),
        "quantity": existing_quantity + quantity,
    }

    save_low_stock_orders(request, orders)


def calculate_order_totals(orders):
    """Calculate total order quantity and monetary value."""

    if not isinstance(orders, dict):
        raise ValueError("Invalid saved orders.")

    total_quantity = 0
    total_value = Decimal(0)

    for product_id, item in orders.items():
        try:
            validated = _validate_saved_order(item)

            if str(product_id) != validated["product_id"]:
                raise ValueError

            quantity = validated["quantity"]
            price = Decimal(validated["price"])

            total_quantity += quantity
            total_value += price * quantity

        except (
            KeyError,
            TypeError,
            ValueError,
            InvalidOperation,
            OverflowError,
        ) as error:
            raise ValueError("Invalid saved order.") from error

    return {
        "total_order_quantity": total_quantity,
        "total_order_value": total_value,
    }
