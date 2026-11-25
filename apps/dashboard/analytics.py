from decimal import Decimal, InvalidOperation

CATEGORY_MAP = {
    "mens-shirts": "Men",
    "mens-shoes": "Men",
    "mens-watches": "Men",
    "tops": "Men",
    "womens-bags": "Women",
    "womens-dresses": "Women",
    "womens-jewellery": "Women",
    "womens-shoes": "Women",
    "womens-watches": "Women",
    "beauty": "Cosmetics",
    "fragrances": "Cosmetics",
    "skin-care": "Cosmetics",
    "laptops": "Electronics",
    "smartphones": "Electronics",
    "tablets": "Electronics",
    "furniture": "Interior Design",
    "home-decoration": "Interior Design",
    "kitchen-accessories": "Interior Design",
    "motorcycle": "Transportation",
    "vehicle": "Transportation",
    "groceries": "Food",
    "mobile-accessories": "Miscellaneous",
    "sports-accessories": "Miscellaneous",
    "sunglasses": "Miscellaneous",
}

DASHBOARD_CATEGORIES = [
    "Men",
    "Women",
    "Electronics",
    "Cosmetics",
    "Interior Design",
    "Transportation",
    "Food",
    "Miscellaneous",
]


class ProductSalesCalculator:
    """Calculate estimated product sales values."""

    @staticmethod
    def calculate_units_sold(product):
        """
        Estimate units sold using:
        max(0, MinimumOrderQuantity - Stock)
        """

        try:
            stock = max(0, int(product.get("stock", 0)))
            minimum = max(0, int(product.get("minimumOrderQuantity", 0)))
        except (TypeError, ValueError, OverflowError):
            return 0

        return max(0, minimum - stock)

    @classmethod
    def calculate_product_sales_value(cls, product):
        try:
            price = Decimal(str(product.get("price", 0)))
        except (InvalidOperation, TypeError, ValueError) as error:
            raise ValueError("Product price must be a valid decimal.") from error

        if not price.is_finite():
            raise ValueError("Product price must be finite.")

        if price < 0:
            price = Decimal(0)

        units_sold = cls.calculate_units_sold(product)

        return Decimal(units_sold) * price

    @classmethod
    def calculate_total_sales(cls, products):
        return sum(
            (cls.calculate_product_sales_value(product) for product in products),
            Decimal(0),
        )


class ProductCategorySalesAggregator:
    """Aggregate sales using API and dashboard categories."""

    @staticmethod
    def get_category(product):
        return CATEGORY_MAP.get(product.get("category", ""))

    @classmethod
    def calculate_business_category_sales(cls, products):
        totals = {category: Decimal(0) for category in DASHBOARD_CATEGORIES}

        unknown = set()

        for product in products:
            api_category = product.get("category") or "Unknown"
            business_category = cls.get_category(product)

            if business_category is None:
                unknown.add(api_category)
                continue

            totals[business_category] += (
                ProductSalesCalculator.calculate_product_sales_value(product)
            )

        return totals, sorted(unknown)

    @staticmethod
    def calculate_api_category_sales(products):
        totals = {}

        for product in products:
            category = product.get("category") or "Unknown"

            value = ProductSalesCalculator.calculate_product_sales_value(product)

            totals[category] = totals.get(category, Decimal(0)) + value

        return dict(sorted(totals.items()))


class ProductStockAnalyzer:
    """Prepare low-stock and out-of-stock inventory records."""

    @staticmethod
    def get_inventory_items(products):
        inventory = []

        for product in products:
            try:
                stock = max(0, int(product.get("stock", 0) or 0))
                minimum = max(0, int(product.get("minimumOrderQuantity", 0) or 0))
            except (TypeError, ValueError, OverflowError):
                continue

            # Include only products at or below minimum stock.
            if stock > minimum:
                continue

            metadata = product.get("meta") or {}

            if not isinstance(metadata, dict):
                metadata = {}

            inventory.append(
                {
                    "id": product.get("id"),
                    "title": product.get("title", "Unknown"),
                    "category": product.get("category", "Unknown"),
                    "sku": product.get("sku", "N/A"),
                    "barcode": metadata.get("barcode", ""),
                    "price": product.get("price", 0),
                    "stock": stock,
                    "minimum_order_quantity": minimum,
                    "rating": product.get("rating"),
                    "availability_status": (
                        product.get("availabilityStatus") or "Unknown"
                    ),
                    "quantity_to_order": "N/A",
                }
            )

        return inventory


# Backward-compatible function interfaces.


def get_category(product):
    return ProductCategorySalesAggregator.get_category(product)


def calculate_product_sales_value(product):
    return ProductSalesCalculator.calculate_product_sales_value(product)


def calculate_total_sales(products):
    return ProductSalesCalculator.calculate_total_sales(products)


def calculate_category_sales(products):
    return ProductCategorySalesAggregator.calculate_business_category_sales(products)


def calculate_api_category_sales(products):
    return ProductCategorySalesAggregator.calculate_api_category_sales(products)


def get_inventory_items(products):
    return ProductStockAnalyzer.get_inventory_items(products)


def get_category_details():
    return [
        {
            "category": category,
            "api_categories": ", ".join(
                api_category.replace("-", " ").title()
                for api_category, business_category in CATEGORY_MAP.items()
                if business_category == category
            ),
        }
        for category in DASHBOARD_CATEGORIES
    ]


def calculate_units_sold(product):
    return ProductSalesCalculator.calculate_units_sold(product)

