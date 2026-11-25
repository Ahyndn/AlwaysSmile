from decimal import Decimal, InvalidOperation

SESSION_KEY = "in_stock_orders"


def _validate_product(product):
    """Validate an eligible in-stock product."""

    if not isinstance(product, dict):
        raise TypeError("Invalid product.")

    product_id = product.get("id")
    if product_id is None or str(product_id).strip() == "":
        raise ValueError("Product ID is required.")

    try:
        stock = int(product.get("stock", 0))
        price = Decimal(str(product.get("price", 0)))
    except (
        TypeError,
        ValueError,
        InvalidOperation,
        OverflowError,
    ) as error:
        raise ValueError("Invalid product information.") from error

    if stock <= 5:
        raise ValueError("Product is not in stock.")

    if not price.is_finite() or price < 0:
        raise ValueError("Invalid product price.")

    return str(product_id), stock, price


def get_in_stock_orders(request):
    """Retrieve saved In Stock orders from the session."""

    orders = request.session.get(SESSION_KEY, {})

    if not isinstance(orders, dict):
        raise ValueError("Invalid saved orders.")  # noqa: TRY004

    return orders


def add_in_stock_order(request, product, quantity):
    """Add a product to saved In Stock orders."""

    product_id, _, price = _validate_product(product)

    try:
        quantity = int(quantity)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError("Invalid quantity.") from error

    if quantity < 1:
        raise ValueError("Quantity must be greater than zero.")

    orders = get_in_stock_orders(request)

    existing = orders.get(product_id, {})

    if existing:
        try:
            existing_quantity = int(existing["quantity"])
            existing_price = Decimal(str(existing["price"]))
        except (
            KeyError,
            TypeError,
            ValueError,
            InvalidOperation,
        ) as error:
            raise ValueError("Invalid existing order.") from error

        if existing_quantity < 1:
            raise ValueError("Invalid existing quantity.")

        if not existing_price.is_finite() or existing_price < 0:
            raise ValueError("Invalid existing price.")

        quantity += existing_quantity

    orders[product_id] = {
        "product_id": product_id,
        "title": str(product.get("title", "Unknown")),
        "price": str(price),
        "quantity": quantity,
    }

    request.session[SESSION_KEY] = orders
    request.session.modified = True

    return orders[product_id]


def delete_in_stock_order(request, product_id):
    """Delete a saved In Stock order."""

    orders = get_in_stock_orders(request)

    product_id = str(product_id)

    if product_id not in orders:
        raise ValueError("Order not found.")

    del orders[product_id]

    request.session[SESSION_KEY] = orders
    request.session.modified = True

    return orders


def clear_in_stock_orders(request):
    """Clear all saved In Stock orders."""

    request.session.pop(SESSION_KEY, None)
    request.session.modified = True


def build_in_stock_orders(products):
    """Return in-stock products with barcode and MOQ information."""

    inventory = []

    for product in products:
        if not isinstance(product, dict):
            continue

        try:
            stock = int(product.get("stock", 0) or 0)
            minimum = int(product.get("minimumOrderQuantity", 0) or 0)
        except (TypeError, ValueError, OverflowError):
            continue

        if stock <= 5:
            continue

        metadata = product.get("meta") or {}

        if not isinstance(metadata, dict):
            metadata = {}

        inventory.append(
            {
                **product,
                "id": product.get("id"),
                "stock": stock,
                "sku": product.get("sku") or "N/A",
                "barcode": metadata.get("barcode") or "",
                "minimum_order_quantity": minimum,
                "availability_status": (product.get("availabilityStatus") or "Unknown"),
            }
        )

    return inventory


def calculate_in_stock_order_totals(orders):
    """Calculate total saved quantity and monetary value."""

    total_quantity = 0
    total_value = Decimal("0.00")

    if not isinstance(orders, dict):
        raise TypeError("Invalid orders.")

    for order in orders.values():
        try:
            quantity = int(order["quantity"])
            price = Decimal(str(order["price"]))
        except (
            KeyError,
            TypeError,
            ValueError,
            InvalidOperation,
        ) as error:
            raise ValueError("Invalid order information.") from error

        if quantity < 1 or not price.is_finite() or price < 0:
            raise ValueError("Invalid order information.")

        total_quantity += quantity
        total_value += price * quantity

    return {
        "total_order_quantity": total_quantity,
        "total_order_value": total_value.quantize(Decimal("0.01")),
    }

