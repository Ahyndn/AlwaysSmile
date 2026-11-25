from decimal import Decimal, InvalidOperation

SESSION_KEY = "out_of_stock_orders"


def _parse_integer(value, field_name):
    """Validate an integer without accepting fractional or Boolean values."""

    if isinstance(value, bool):
        raise ValueError(f"Invalid {field_name}.")

    try:
        parsed = int(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError(f"Invalid {field_name}.") from error

    if isinstance(value, (float, Decimal)):
        if not Decimal(str(value)).is_finite():
            raise ValueError(f"Invalid {field_name}.")

        if Decimal(str(value)) != Decimal(parsed):
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


def get_out_of_stock_orders(request):
    """Retrieve and validate saved orders from the session."""

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


def save_out_of_stock_orders(request, orders):
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


def clear_out_of_stock_orders(request):
    """Remove all saved out-of-stock orders."""

    request.session.pop(SESSION_KEY, None)
    request.session.modified = True


def delete_out_of_stock_order(request, product_id):
    """Delete an order without failing when it does not exist."""

    orders = get_out_of_stock_orders(request)

    orders.pop(str(product_id), None)

    save_out_of_stock_orders(request, orders)


def build_out_of_stock_orders(products):
    """Return valid out-of-stock products with barcode and MOQ."""

    results = []

    for product in products:
        if not isinstance(product, dict):
            continue

        try:
            stock = _parse_integer(
                product.get("stock", 0) or 0,
                "stock",
            )

            minimum = _parse_integer(
                product.get("minimumOrderQuantity", 0) or 0,
                "minimum order quantity",
            )

            price = _parse_price(product.get("price", 0))

            if stock < 0 or minimum < 0:
                continue

        except ValueError:
            continue

        if stock != 0:
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
                "barcode": metadata.get("barcode") or "",
                "price": price,
                "stock": stock,
                "minimum_order_quantity": minimum,
                "availability_status": (product.get("availabilityStatus") or "Unknown"),
                "quantity_to_order": max(1, minimum - stock),
            }
        )

    return results


def add_out_of_stock_order(request, product, quantity):
    """Add or accumulate a validated order in session memory."""

    if not isinstance(product, dict):
        raise ValueError("Invalid product.")

    quantity = _parse_integer(quantity, "order quantity")

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

        price = _parse_price(product.get("price", 0))

    except ValueError as error:
        raise ValueError("Invalid product information.") from error

    if stock != 0:
        raise ValueError("Product is no longer out of stock.")

    # Validate the complete existing session before modifying it.
    orders = get_out_of_stock_orders(request)

    existing = orders.get(product_id)

    existing_quantity = 0

    if existing is not None:
        existing_quantity = existing["quantity"]

    orders[product_id] = {
        "product_id": product_id,
        "title": str(product.get("title") or "Unknown"),
        "price": str(price),
        "quantity": existing_quantity + quantity,
    }

    save_out_of_stock_orders(request, orders)


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
